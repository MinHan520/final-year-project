"""Scan orchestrator — Multi-Modal Forensic Pipeline.

Stage order (matches System Architecture flowchart):
  1. object_classification  — instant file-type detection (no LLM)
  2. aide                   — AIDE mixture-of-experts detector (PyTorch)
  3. opencv_maps            — low-level forensic maps (OpenCV, local)
  4. opencv_commentary      — plain-English VLM explanation (Gemini)
  5. synthid                — SynthID watermark check (Gemini)
  6. conflict               — conflict resolution (new rules A/B/C/E)
  7. eval                   — Final Verdict + Confidence Score (Gemini)

Design choices:
  * Each agent call is wrapped in asyncio.to_thread (all agents are blocking).
  * Stages emit stage_start / stage_result events; eval may also emit stage_chunk.
  * Per-stage exceptions are captured as stage_error — one failure does not abort
    the whole scan.
  * AIDE is the only hard dependency; without it the pipeline short-circuits.
  * HIGH/MEDIUM conflict severity pauses the pipeline via asyncio.Event until a
    human decision arrives (POST /api/scan/{id}/resolve_conflict) or
    HUMAN_REVIEW_TIMEOUT_SECONDS elapses.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from .agents import (
    AIDEDetectorAgent,
    ConflictResolutionAgent,
    GeminiRouterAgent,
    ObjectClassificationAgent,
    OpenCVForensicsAgent,
    SynthIDAgent,
)
from .agents.gemini_router import detect_media_type
from .config import Settings
from .event_bus import EventBus
from .schemas import (
    AIDEResult,
    ConflictResult,
    ObjectClassificationResult,
    OpenCVComments,
    SynthIDResult,
)
from .storage import ScanStore, classify_risk

logger = logging.getLogger(__name__)

HUMAN_REVIEW_TIMEOUT_SECONDS = 300
MAX_RECLASSIFICATION_ATTEMPTS = 2

# Module-level state shared with routes_scan for the human-in-the-loop flow.
# Maps scan_id → asyncio.Event that the resolve endpoint sets to unblock run_scan.
_pending_reviews: dict[str, asyncio.Event] = {}
# Maps scan_id → {"decision": str, "reason": str} populated by the resolve endpoint.
_review_decisions: dict[str, dict] = {}

_ANOMALY_KEYWORDS = frozenset({
    "ai", "generated", "artificial", "inconsisten", "anomal",
    "artifact", "unusual", "suspicious", "manipulat", "synthetic",
})


def _detect_opencv_anomalies(comments: OpenCVComments) -> bool:
    """Derive a boolean anomaly flag from VLM commentary text."""
    combined = f"{comments.noise} {comments.edges} {comments.compression}".lower()
    # Fallback comments mean GCP wasn't available — treat as no analysis done.
    if "check your gemini api" in combined:
        return False
    return any(kw in combined for kw in _ANOMALY_KEYWORDS)


async def _run_stage(
    bus: EventBus,
    scan_id: str,
    agent: str,
    label: str,
    coro_factory,
) -> Optional[Any]:
    """Emit start/result events around a single agent call."""
    await bus.publish(scan_id, "stage_start", {"agent": agent, "label": label})
    try:
        result = await coro_factory()
    except Exception as e:
        logger.exception("Stage %s failed for scan %s", agent, scan_id)
        await bus.publish(scan_id, "stage_error", {"agent": agent, "message": str(e)})
        return None

    payload = result.model_dump() if hasattr(result, "model_dump") else result
    await bus.publish(scan_id, "stage_result", {"agent": agent, "result": payload})
    return result




async def run_scan(
    scan_id: str,
    file_path: Path,
    detector: Optional[AIDEDetectorAgent],
    settings: Settings,
    bus: EventBus,
    store: ScanStore,
    media_type: str = "image",
) -> None:
    """Top-level orchestrator. Runs every agent, persists final summary."""
    summary: dict[str, Any] = {"scan_id": scan_id}
    project_id = settings.gcp_project_id
    location = settings.gcp_location

    try:
        await asyncio.to_thread(store.update_status, scan_id, "running")

        # ── Stage 1: Object Classification ──────────────────────────────────
        classification = await _run_stage(
            bus,
            scan_id,
            agent="object_classification",
            label="Object Classification",
            coro_factory=lambda: asyncio.to_thread(
                ObjectClassificationAgent.classify, file_path, project_id, location
            ),
        )
        if classification is not None:
            summary["object_classification"] = classification.model_dump()
            detected_type = classification.media_type
        else:
            detected_type = media_type

        # ── Non-image short-circuit ──────────────────────────────────────────
        if detected_type != "image":
            msg = (
                f"Object Classification Agent determined this is a {detected_type}. "
                "Our detection pipeline for this media type is currently under "
                "development and will be available soon."
            )
            summary["eval"] = {"text": msg, "success": False}
            await asyncio.to_thread(
                store.finalize,
                scan_id,
                "complete",
                result=summary,
                score=None,
                risk_label=None,
            )
            await bus.publish(scan_id, "complete", {"scan_id": scan_id, "summary": summary})
            return

        # ── Stage 2: AIDE Detection ──────────────────────────────────────────
        if detector is None:
            err = "AIDE detector not loaded; set AIDE_CHECKPOINT_PATH in env."
            await bus.publish(scan_id, "stage_error", {"agent": "aide", "message": err})
            await asyncio.to_thread(store.finalize, scan_id, "failed", error=err)
            await bus.publish(scan_id, "error", {"scan_id": scan_id, "message": err})
            return

        aide: Optional[AIDEResult] = await _run_stage(
            bus,
            scan_id,
            agent="aide",
            label="AIDE Detection",
            coro_factory=lambda: asyncio.to_thread(detector.predict, file_path),
        )
        score: Optional[float] = None
        if aide is not None and aide.success:
            score = aide.score
            summary["aide"] = aide.model_dump()

        # ── Stage 3: Low Level Artifact Analysis ─────────────────────────────
        maps = await _run_stage(
            bus,
            scan_id,
            agent="opencv_maps",
            label="Low Level Artifact Analysis",
            coro_factory=lambda: asyncio.to_thread(
                OpenCVForensicsAgent.compute_maps, file_path
            ),
        )
        if maps is not None:
            summary["opencv_maps"] = maps.model_dump()

        comments_result = await _run_stage(
            bus,
            scan_id,
            agent="opencv_commentary",
            label="Low Level Artifact Analysis",
            coro_factory=lambda: asyncio.to_thread(
                OpenCVForensicsAgent.explain_with_vlm,
                file_path,
                project_id,
                location,
            ),
        )
        opencv_comments = (
            comments_result
            if comments_result is not None
            else OpenCVComments(noise="", edges="", compression="")
        )
        summary["opencv_commentary"] = opencv_comments.model_dump()

        # ── Stage 4: SynthID Detection ───────────────────────────────────────
        synthid_result: Optional[SynthIDResult] = await _run_stage(
            bus,
            scan_id,
            agent="synthid",
            label="SynthID Detection",
            coro_factory=lambda: asyncio.to_thread(
                SynthIDAgent.check, file_path, project_id, location
            ),
        )
        synthid = (
            synthid_result
            if synthid_result is not None
            else SynthIDResult(is_ai=None, reasoning="SynthID stage skipped.")
        )
        summary["synthid"] = synthid.model_dump()

        # ── Stage 5: Conflict Resolution ─────────────────────────────────────
        conflict: Optional[ConflictResult] = None
        if aide is not None and aide.success:
            opencv_anomalies = _detect_opencv_anomalies(opencv_comments)

            attempt = 0
            while True:
                conflict = await _run_stage(
                    bus,
                    scan_id,
                    agent="conflict",
                    label="Conflict Resolution",
                    coro_factory=lambda: asyncio.to_thread(
                        ConflictResolutionAgent.evaluate,
                        aide.score,
                        synthid,
                        opencv_anomalies,
                    ),
                )
                if conflict is None or conflict.action_required != "human_review":
                    break

                # Pause pipeline — wait for human decision via resolve endpoint.
                review_event = asyncio.Event()
                _pending_reviews[scan_id] = review_event
                await bus.publish(
                    scan_id,
                    "human_review_required",
                    {"scan_id": scan_id, "conflict": conflict.model_dump()},
                )
                logger.info(
                    "Scan %s paused for human review (rule %s, severity %s)",
                    scan_id, conflict.rule_triggered, conflict.severity,
                )

                try:
                    await asyncio.wait_for(
                        review_event.wait(),
                        timeout=HUMAN_REVIEW_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "Human review timed out for scan %s after %ds; proceeding.",
                        scan_id, HUMAN_REVIEW_TIMEOUT_SECONDS,
                    )
                    _pending_reviews.pop(scan_id, None)
                    _review_decisions.pop(scan_id, None)
                    break

                decision_data = _review_decisions.pop(scan_id, {})
                _pending_reviews.pop(scan_id, None)

                decision = decision_data.get("decision", "proceed")
                if decision != "reclassify" or attempt >= MAX_RECLASSIFICATION_ATTEMPTS:
                    break

                attempt += 1
                # Loop: re-run conflict evaluation and prompt human again.

            if conflict is not None:
                summary["conflict"] = conflict.model_dump()

        # ── Stage 6: Final Verdict ────────────────────────────────────────────
        if score is not None and project_id:
            eval_result = await _run_stage(
                bus,
                scan_id,
                agent="eval",
                label="Final Verdict",
                coro_factory=lambda: asyncio.to_thread(
                    GeminiRouterAgent.evaluate_image,
                    file_path,
                    score,
                    synthid,
                    opencv_comments,
                    project_id,
                    location,
                    conflict,
                ),
            )
            if eval_result is not None:
                summary["eval"] = eval_result.model_dump()

        # ── Persist + signal completion ──────────────────────────────────────
        risk_label = classify_risk(score) if score is not None else None
        await asyncio.to_thread(
            store.finalize,
            scan_id,
            "complete",
            result=summary,
            score=score,
            risk_label=risk_label,
        )
        await bus.publish(scan_id, "complete", {"scan_id": scan_id, "summary": summary})
    except Exception as e:
        logger.exception("Scan %s failed", scan_id)
        await asyncio.to_thread(store.finalize, scan_id, "failed", error=str(e))
        await bus.publish(scan_id, "error", {"scan_id": scan_id, "message": str(e)})
    finally:
        _pending_reviews.pop(scan_id, None)
        _review_decisions.pop(scan_id, None)
        await bus.close(scan_id)

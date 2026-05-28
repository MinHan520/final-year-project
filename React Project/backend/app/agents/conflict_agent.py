"""Conflict Resolution Agent — Rules v1.1.

Sequential state-machine ruleset. Evaluated top-to-bottom; the first rule
that fires returns immediately with a final_verdict and optional action.

Rules:
  1 — Watermark Confirmed:      synthid.watermark_found AND watermark_confidence >= 0.90
  2 — Dual High-Confidence:     aide >= 0.75 AND synthid.confidence >= 0.70
  3 — AIDE High, No Corroboration: aide >= 0.75 AND synthid.confidence < 0.70 AND opencv < 0.50  → HITL
  4 — Dual Inconclusive:        0.40 <= aide <= 0.74 AND 0.40 <= synthid.confidence <= 0.74
  5 — Default Terminal:         catch-all → Likely Authentic
"""

from __future__ import annotations

import json
import logging

from ..schemas import ConflictResult, ConflictSeverity

logger = logging.getLogger(__name__)


class ConflictResolutionAgent:
    """Pure logic agent — no LLM required."""

    @staticmethod
    def evaluate(
        aide_score: float,
        synthid_result,
        opencv_anomaly_score: float,
    ) -> ConflictResult:
        logger.info(
            "[ConflictAgent] Evaluating signals — AIDE score: %.4f | "
            "SynthID watermark: %s | SynthID watermark_confidence: %.4f | "
            "SynthID confidence: %.4f | OpenCV anomaly score: %.4f",
            aide_score,
            synthid_result.watermark_found,
            synthid_result.watermark_confidence,
            synthid_result.confidence,
            opencv_anomaly_score,
        )

        # ── Rule 1: Watermark Confirmed ──────────────────────────────────────
        if synthid_result.watermark_found:
            # watermark_confidence is a separate field that the SynthID agent
            # may not populate. Fall back to the overall synthid.confidence
            # (which _compute_confidence already sets to 0.99 for watermark hits).
            effective_wm_confidence = (
                synthid_result.watermark_confidence
                if synthid_result.watermark_confidence > 0.0
                else synthid_result.confidence
            )
            if effective_wm_confidence >= 0.90:
                logger.info("[ConflictAgent] RULE_1_WATERMARK_TRIGGER fired.")
                result = ConflictResult(
                    has_conflict           = False,
                    rule_triggered         = "1",
                    reason                 = "Cryptographic watermark detected with high confidence.",
                    action_required        = "proceed",
                    final_verdict          = "AI-Generated (Watermark Found)",
                    final_confidence_score = effective_wm_confidence,
                )
                logger.info("[ConflictAgent] Rule 1 result:\n%s", json.dumps(result.model_dump(), indent=2))
                return result
            else:
                logger.info(
                    "[ConflictAgent] WATERMARK_LOW_CONFIDENCE_BYPASSED "
                    "(effective_wm_confidence=%.4f < 0.90). Continuing evaluation.",
                    effective_wm_confidence,
                )

        # ── Rule 2: Dual High-Confidence ─────────────────────────────────────
        if aide_score >= 0.75 and synthid_result.confidence >= 0.70:
            logger.info("[ConflictAgent] RULE_2_DUAL_HIGH_CONFIDENCE_TRIGGER fired.")
            result = ConflictResult(
                has_conflict           = False,
                rule_triggered         = "2",
                reason                 = "Both AIDE and SynthID report high-confidence AI generation.",
                action_required        = "proceed",
                confidence_gap         = abs(aide_score - synthid_result.confidence),
                final_verdict          = "AI-Generated",
                final_confidence_score = (aide_score + synthid_result.confidence) / 2,
            )
            logger.info("[ConflictAgent] Rule 2 result:\n%s", json.dumps(result.model_dump(), indent=2))
            return result

        # ── Rule 3: AIDE High, No Corroboration → HITL ───────────────────────
        if (
            aide_score >= 0.75
            and synthid_result.confidence < 0.70
            and opencv_anomaly_score < 0.50
        ):
            logger.info("[ConflictAgent] RULE_3_HITL_REQUIRED fired.")
            result = ConflictResult(
                has_conflict        = True,
                severity            = ConflictSeverity.HIGH,
                conflicting_signals = ["aide_score", "synthid_confidence", "opencv"],
                rule_triggered      = "3",
                reason              = (
                    "AIDE reports high AI probability but SynthID and OpenCV "
                    "do not corroborate. Human review required."
                ),
                action_required     = "human_review",
                confidence_gap      = abs(aide_score - synthid_result.confidence),
            )
            logger.info("[ConflictAgent] Rule 3 result:\n%s", json.dumps(result.model_dump(), indent=2))
            return result

        # ── Rule 4: Dual Inconclusive ─────────────────────────────────────────
        if (
            0.40 <= aide_score <= 0.74
            and 0.40 <= synthid_result.confidence <= 0.74
        ):
            logger.info("[ConflictAgent] RULE_4_DUAL_INCONCLUSIVE_TRIGGER fired.")
            result = ConflictResult(
                has_conflict           = True,
                severity               = ConflictSeverity.MEDIUM,
                conflicting_signals    = ["aide_score", "synthid_confidence"],
                rule_triggered         = "4",
                reason                 = "Both AIDE and SynthID returned inconclusive mid-range scores.",
                action_required        = "proceed",
                confidence_gap         = abs(aide_score - synthid_result.confidence),
                final_verdict          = "High Chances AI-Generated",
                final_confidence_score = (aide_score + synthid_result.confidence) / 2,
            )
            logger.info("[ConflictAgent] Rule 4 result:\n%s", json.dumps(result.model_dump(), indent=2))
            return result

        # ── Rule 5: Default Terminal (Fallback to Max Score) ──────────────────
        max_score = max(aide_score, synthid_result.confidence)
        
        if max_score >= 0.80:
            final_verdict = "AI-Generated"
        elif max_score >= 0.50:
            final_verdict = "High Chances AI-Generated"
        elif max_score >= 0.30:
            final_verdict = "Inconclusive"
        else:
            final_verdict = "Likely Authentic"

        if aide_score >= 0.75 and opencv_anomaly_score >= 0.50:
            logger.info(
                "[ConflictAgent] RULE_5_AIDE_OPENCV_CORROBORATED "
                "(aide=%.4f, opencv=%.4f) — defaulting to terminal verdict.",
                aide_score,
                opencv_anomaly_score,
            )
        else:
            logger.info("[ConflictAgent] RULE_5_DEFAULT_TERMINAL fired. max_score=%.4f", max_score)

        result = ConflictResult(
            has_conflict           = False,
            rule_triggered         = "5",
            reason                 = "No decisive conflicting signals. Verdict derived from maximum detection score.",
            action_required        = "proceed",
            final_verdict          = final_verdict,
            final_confidence_score = max_score,
        )
        logger.info("[ConflictAgent] Rule 5 result:\n%s", json.dumps(result.model_dump(), indent=2))
        return result


# Backward-compat alias used by existing imports
ConflictAgent = ConflictResolutionAgent

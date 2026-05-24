"""Scan endpoints.

  * POST /api/scan                  → 202 + scan_id, kicks off background scan
  * GET  /api/scan/{scan_id}        → final JSON for a completed scan
  * GET  /api/scan/{scan_id}/events → SSE stream of stage events
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ..agents.gemini_router import detect_media_type
from ..agents.shap_explainer import SHAPExplainerAgent
from ..orchestrator import run_scan, _pending_reviews, _review_decisions
from ..detector_loader import get_detector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["scan"])

_shap_lock = asyncio.Lock()


class ResolveConflictRequest(BaseModel):
    decision: str  # "proceed" | "reclassify"
    reason: str


@router.post("/scan", status_code=202)
async def create_scan(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> JSONResponse:
    media_type = detect_media_type(file.filename)

    settings = request.app.state.settings
    upload_dir: Path = settings.upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)

    scan_id = uuid.uuid4().hex
    suffix = Path(file.filename or "upload").suffix.lower() or ".bin"
    saved_path = upload_dir / f"{scan_id}{suffix}"
    content = await file.read()
    await asyncio.to_thread(saved_path.write_bytes, content)

    store = request.app.state.store
    await asyncio.to_thread(
        store.create, scan_id, file.filename or saved_path.name, media_type
    )

    # Lazy load the detector if not already loaded
    detector = await get_detector(request.app)

    background_tasks.add_task(
        run_scan,
        scan_id,
        saved_path,
        detector,
        settings,
        request.app.state.bus,
        store,
        media_type,
    )

    return JSONResponse(
        status_code=202,
        content={
            "scan_id": scan_id,
            "stream_url": f"/api/scan/{scan_id}/events",
            "result_url": f"/api/scan/{scan_id}",
        },
    )


@router.get("/scan/{scan_id}")
async def get_scan(scan_id: str, request: Request) -> dict[str, Any]:
    store = request.app.state.store
    record = await asyncio.to_thread(store.get, scan_id)
    if record is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return record


@router.get("/scan/{scan_id}/events")
async def stream_scan_events(scan_id: str, request: Request) -> EventSourceResponse:
    bus = request.app.state.bus
    store = request.app.state.store

    async def event_source() -> AsyncIterator[dict[str, Any]]:
        # If the bus has no live queue, the scan is either unknown or
        # already finished. Replay terminal state so late joiners aren't
        # left hanging.
        if not bus.has_active(scan_id):
            record = await asyncio.to_thread(store.get, scan_id)
            if record is None:
                yield {
                    "event": "error",
                    "data": json.dumps({"message": "scan not found"}),
                }
                return
            event_name = "complete" if record["status"] == "complete" else "error"
            payload = {
                "scan_id": scan_id,
                "summary": record.get("result"),
                "status": record["status"],
                "error": record.get("error"),
            }
            yield {"event": event_name, "data": json.dumps(payload)}
            return

        async for event in bus.subscribe(scan_id):
            if await request.is_disconnected():
                break
            yield {"event": event.name, "data": json.dumps(event.data)}

    return EventSourceResponse(event_source())

@router.post("/scan/{scan_id}/shap")
async def run_shap(scan_id: str, request: Request) -> dict[str, Any]:
    store = request.app.state.store
    record = await asyncio.to_thread(store.get, scan_id)
    if record is None:
        raise HTTPException(status_code=404, detail="scan not found")

    settings = request.app.state.settings
    upload_dir: Path = settings.upload_dir
    suffix = Path(record["filename"]).suffix.lower() or ".bin"
    file_path = upload_dir / f"{scan_id}{suffix}"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Original image not found")

    # Lazy load the detector if not already loaded
    detector = await get_detector(request.app)
    if not detector:
        raise HTTPException(status_code=503, detail="AIDE detector unavailable")

    async with _shap_lock:
        explainer = SHAPExplainerAgent(detector)
        result = await asyncio.to_thread(explainer.explain, file_path)

    summary = record.get("result") or {}
    summary["shap"] = result.model_dump()

    await asyncio.to_thread(
        store.finalize,
        scan_id,
        "complete",
        result=summary,
        score=record.get("score"),
        risk_label=record.get("risk_label"),
    )

    updated_record = await asyncio.to_thread(store.get, scan_id)
    return updated_record


@router.post("/scan/{scan_id}/resolve_conflict")
async def resolve_conflict(
    scan_id: str,
    body: ResolveConflictRequest,
    request: Request,
) -> dict:
    """Unblock a pipeline paused for human review.

    The orchestrator's asyncio.Event is set here, allowing run_scan to
    continue after reading the stored decision.
    """
    if body.decision not in {"proceed", "reclassify"}:
        raise HTTPException(
            status_code=422,
            detail=f"decision must be 'proceed' or 'reclassify', got '{body.decision}'",
        )
    if not body.reason.strip():
        raise HTTPException(status_code=422, detail="reason is required and cannot be blank")

    event = _pending_reviews.get(scan_id)
    if event is None:
        raise HTTPException(
            status_code=404,
            detail="No pending human review found for this scan. "
                   "It may have already been resolved or timed out.",
        )

    _review_decisions[scan_id] = {"decision": body.decision, "reason": body.reason}
    event.set()
    logger.info("Conflict resolved for scan %s: decision=%s", scan_id, body.decision)
    return {"status": "ok", "scan_id": scan_id, "decision": body.decision}

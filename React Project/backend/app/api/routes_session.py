"""Session-scoped scan listing.

Phase 1 has a single implicit session — every scan belongs to the "current"
one. Real session/user separation comes with auth in a later phase.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["session"])


@router.get("/sessions/current/scans")
async def list_scans(request: Request, limit: int = 50) -> list[dict[str, Any]]:
    store = request.app.state.store
    return await asyncio.to_thread(store.list_recent, limit)


@router.delete("/scans/{scan_id}", status_code=204)
async def delete_scan(scan_id: str, request: Request) -> None:
    store = request.app.state.store
    deleted = await asyncio.to_thread(store.delete, scan_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="scan not found")

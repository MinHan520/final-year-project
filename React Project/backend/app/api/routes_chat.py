from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..agents.gemini_router import GeminiRouterAgent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

class ChatMessage(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    scan_id: str | None = None
    message: str
    history: list[ChatMessage] = []

@router.post("/chat")
async def chat_endpoint(req: ChatRequest, request: Request) -> dict[str, Any]:
    if not req.message.strip():
        return {"reply": "Please provide a message.", "used_scan_id": req.scan_id}

    store = request.app.state.store
    project_id = request.app.state.settings.gcp_project_id
    location = request.app.state.settings.gcp_location

    scan_summary_text = ""
    if req.scan_id:
        record = await asyncio.to_thread(store.get, req.scan_id)
        if record and record.get("status") == "complete":
            summary = record.get("result", {})
            eval_text = summary.get("eval", {}).get("text", "")
            aide_score = summary.get("aide", {}).get("score", 0)
            scan_summary_text = f"[Context: The active scan '{record.get('filename')}' is complete with an AI probability score of {aide_score:.2f}. The final evaluation verdict is: {eval_text}]"

    history_dicts = [{"role": m.role, "text": m.text} for m in req.history]
    if scan_summary_text:
        history_dicts.insert(0, {"role": "system", "text": scan_summary_text})

    agent = GeminiRouterAgent()
    reply = await asyncio.to_thread(
        agent.conversational_reply,
        user_text=req.message,
        history=history_dicts,
        project_id=project_id,
        location=location,
    )

    return {"reply": reply, "used_scan_id": req.scan_id}

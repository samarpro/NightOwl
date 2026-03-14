"""Shadow agent API — chat with a toolless clone of a running session."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["shadow"])


class ShadowMessage(BaseModel):
    message: str


@router.post("/sessions/{session_id}/shadow")
async def create_shadow(session_id: str, request: Request) -> dict[str, str]:
    """Create a shadow agent for a live session."""
    shadow_manager = request.app.state.shadow_manager
    try:
        shadow_id = await shadow_manager.create(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"shadow_id": shadow_id, "session_id": session_id}


@router.post("/shadow/{shadow_id}/message")
async def shadow_message(shadow_id: str, body: ShadowMessage, request: Request) -> dict[str, Any]:
    """Chat with a shadow agent."""
    shadow_manager = request.app.state.shadow_manager
    try:
        reply = await shadow_manager.message(shadow_id, body.message)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"reply": reply, "shadow_id": shadow_id}


@router.post("/shadow/{shadow_id}/correct")
async def shadow_correct(shadow_id: str, body: ShadowMessage, request: Request) -> dict[str, str]:
    """Send a correction from the shadow to the live agent."""
    shadow_manager = request.app.state.shadow_manager
    try:
        await shadow_manager.correct(shadow_id, body.message)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "sent", "shadow_id": shadow_id}


@router.delete("/shadow/{shadow_id}")
async def destroy_shadow(shadow_id: str, request: Request) -> dict[str, str]:
    """Destroy a shadow agent."""
    request.app.state.shadow_manager.destroy(shadow_id)
    return {"status": "destroyed", "shadow_id": shadow_id}

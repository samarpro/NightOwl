"""Shared ingest router."""

from __future__ import annotations

from fastapi import APIRouter, Request

from nightowl.models.message import ChannelMessage

router = APIRouter(prefix="/api/v1/message", tags=["ingest"])


@router.post("/ingest")
async def ingest_message(message: ChannelMessage, request: Request) -> dict[str, object]:
    result = await request.app.state.ingress_service.ingest(message)
    return {"sessionId": result.session_id, "created": result.created}

"""Realtime websocket router."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

router = APIRouter(tags=["websocket"])


class ApprovalRespondMessage(BaseModel):
    type: str = Field(pattern=r"^approval\.respond$")
    approval_id: str
    approved: bool
    reason: str | None = None


@router.websocket("/ws")
async def websocket_events(websocket: WebSocket) -> None:
    await websocket.accept()
    broadcaster = websocket.app.state.broadcaster
    gate = websocket.app.state.hitl_gate

    async def sender() -> None:
        async for event in broadcaster.subscribe():
            await websocket.send_json(event)

    sender_task = asyncio.create_task(sender(), name="ws-sender")
    try:
        while True:
            payload = await websocket.receive_json()
            if payload.get("type") != "approval.respond":
                continue
            message = ApprovalRespondMessage.model_validate(payload)
            gate.resolve_approval(
                message.approval_id,
                approved=message.approved,
                reason=message.reason,
            )
    except WebSocketDisconnect:
        pass
    finally:
        sender_task.cancel()
        await asyncio.gather(sender_task, return_exceptions=True)

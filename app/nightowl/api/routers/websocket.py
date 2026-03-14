"""Realtime websocket router."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import AliasChoices, BaseModel, Field

from nightowl.events.schemas import RuntimeEvent
from nightowl.models.approval import ApprovalDecision

router = APIRouter(tags=["websocket"])


class ApprovalRespondMessage(BaseModel):
    type: str = Field(pattern=r"^approval\.respond$")
    approval_id: str
    decision: ApprovalDecision
    reason: str | None = None
    redirect_message: str | None = None


class DashboardSubscribeMessage(BaseModel):
    type: str = Field(pattern=r"^dashboard\.subscribe$")
    session_id: str | None = Field(default=None, validation_alias=AliasChoices("sessionId", "session_id"))


async def _send_dashboard_snapshot(websocket: WebSocket, session_id: str | None = None) -> None:
    store = websocket.app.state.manager.store
    root_sessions = await store.list_root_sessions() if store else []
    child_sessions = await store.list_child_sessions(session_id) if store and session_id else []
    event = RuntimeEvent(
        event_id=f"event:{uuid.uuid4().hex[:12]}",
        event_type="dashboard.snapshot",
        occurred_at=datetime.now(UTC),
        session_id=session_id,
        payload={
            "rootSessions": root_sessions,
            "childSessions": child_sessions,
            "selectedSessionId": session_id,
        },
    )
    await websocket.send_json(event.model_dump(mode="json", by_alias=True))


@router.websocket("/ws")
async def websocket_events(websocket: WebSocket) -> None:
    await websocket.accept()
    broadcaster = websocket.app.state.broadcaster
    gate = websocket.app.state.hitl_gate
    await _send_dashboard_snapshot(websocket)

    async def sender() -> None:
        async for event in broadcaster.subscribe():
            await websocket.send_json(event)

    sender_task = asyncio.create_task(sender(), name="ws-sender")
    try:
        while True:
            payload = await websocket.receive_json()
            message_type = payload.get("type")
            if message_type == "dashboard.subscribe":
                message = DashboardSubscribeMessage.model_validate(payload)
                await _send_dashboard_snapshot(websocket, message.session_id)
                continue
            if message_type != "approval.respond":
                continue
            message = ApprovalRespondMessage.model_validate(payload)
            gate.resolve_approval(
                message.approval_id,
                decision=message.decision,
                reason=message.reason,
                redirect_message=message.redirect_message,
            )
    except WebSocketDisconnect:
        pass
    finally:
        sender_task.cancel()
        await asyncio.gather(sender_task, return_exceptions=True)

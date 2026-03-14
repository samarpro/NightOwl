"""Translate internal runtime events into websocket-safe envelopes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from nightowl.events.schemas import RuntimeEvent
from nightowl.sessions.store import serialize_session


def _preview(text: str | None, limit: int = 140) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return f"{text[:limit - 3]}..."


def _session_updated_payload(raw: dict[str, Any], status: str) -> RuntimeEvent:
    session = raw.get("session", {})
    session_payload = serialize_session({
        **session,
        "id": session.get("id", raw.get("session_id")),
        "state": status,
        "result": session.get("result", raw.get("result")),
    })
    return RuntimeEvent(
        event_id=f"event:{uuid.uuid4().hex[:12]}",
        event_type="session.updated",
        occurred_at=datetime.now(UTC),
        session_id=session_payload["id"],
        channel=raw.get("channel"),
        payload=session_payload,
    )


def translate_runtime_event(raw: dict[str, Any]) -> RuntimeEvent | None:
    raw_type = raw.get("type")
    if not raw_type:
        return None

    if raw_type == "session:created":
        session = raw.get("session", {})
        session_id = session.get("id")
        return RuntimeEvent(
            event_id=f"event:{uuid.uuid4().hex[:12]}",
            event_type="session.created",
            occurred_at=datetime.now(UTC),
            session_id=session_id,
            channel=raw.get("channel"),
            payload=serialize_session(session),
        )

    if raw_type == "session:resumed":
        return RuntimeEvent(
            event_id=f"event:{uuid.uuid4().hex[:12]}",
            event_type="session.resumed",
            occurred_at=datetime.now(UTC),
            session_id=raw.get("session_id"),
            channel=raw.get("channel"),
            payload={
                "sessionId": raw.get("session_id"),
                "channel": raw.get("channel"),
                "reason": raw.get("reason", "inbound_channel_message"),
            },
        )

    if raw_type == "session:running":
        return _session_updated_payload(raw, "running")
    if raw_type == "session:waiting":
        return _session_updated_payload(raw, "waiting")
    if raw_type == "session:completed":
        return _session_updated_payload(
            {
                **raw,
                "current_intent": raw.get("current_intent", ""),
                "wait_reason": None,
            },
            "completed" if raw.get("success", True) else "failed",
        )
    if raw_type == "session:spawned":
        child = raw.get("child", {})
        return RuntimeEvent(
            event_id=f"event:{uuid.uuid4().hex[:12]}",
            event_type="session.created",
            occurred_at=datetime.now(UTC),
            session_id=child.get("id"),
            payload=serialize_session(child),
        )

    if raw_type == "channel:message_received":
        return RuntimeEvent(
            event_id=f"event:{uuid.uuid4().hex[:12]}",
            event_type="channel.message_received",
            occurred_at=datetime.now(UTC),
            session_id=raw.get("session_id"),
            channel=raw.get("channel"),
            payload={
                "channel": raw.get("channel"),
                "chatId": raw.get("chat_id"),
                "senderId": raw.get("sender_id"),
                "textPreview": _preview(raw.get("text")),
                "messageId": raw.get("message_id"),
            },
        )

    if raw_type == "channel:reply_queued":
        event_type = "channel.reply_queued"
    elif raw_type == "channel:reply_sent":
        event_type = "channel.reply_sent"
    elif raw_type == "channel:reply_failed":
        event_type = "channel.reply_failed"
    else:
        event_type = None
    if event_type:
        return RuntimeEvent(
            event_id=f"event:{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            occurred_at=datetime.now(UTC),
            session_id=raw.get("session_id"),
            channel=raw.get("channel"),
            payload={
                "sessionId": raw.get("session_id"),
                "channel": raw.get("channel"),
                "chatId": raw.get("chat_id"),
                "textPreview": _preview(raw.get("text")),
                "messageId": raw.get("message_id"),
                "error": raw.get("error"),
            },
        )

    if raw_type == "agent:response":
        return RuntimeEvent(
            event_id=f"event:{uuid.uuid4().hex[:12]}",
            event_type="agent.response",
            occurred_at=datetime.now(UTC),
            session_id=raw.get("session_id"),
            channel=raw.get("channel"),
            payload={
                "sessionId": raw.get("session_id"),
                "text": raw.get("text", ""),
                "textPreview": _preview(raw.get("text")),
            },
        )

    if raw_type == "approval:required":
        return RuntimeEvent(
            event_id=f"event:{uuid.uuid4().hex[:12]}",
            event_type="approval.requested",
            occurred_at=datetime.now(UTC),
            session_id=raw.get("session_id"),
            channel=raw.get("channel"),
            payload={
                "id": raw.get("approval_id"),
                "sessionId": raw.get("session_id"),
                "title": f"Approve {raw.get('tool_name', 'tool')}",
                "toolName": raw.get("tool_name"),
                "reason": raw.get("reason", ""),
                "riskLevel": str(raw.get("risk_level", "medium")),
                "expiresAt": raw.get("expires_at"),
                "status": "pending",
            },
        )

    if raw_type == "approval:resolved":
        return RuntimeEvent(
            event_id=f"event:{uuid.uuid4().hex[:12]}",
            event_type="approval.resolved",
            occurred_at=datetime.now(UTC),
            session_id=raw.get("session_id"),
            channel=raw.get("channel"),
            payload={
                "approvalId": raw.get("approval_id"),
                "decision": raw.get("decision"),
                "reason": raw.get("reason"),
                "redirectMessage": raw.get("redirect_message"),
            },
        )

    if raw_type == "approval:timeout":
        return RuntimeEvent(
            event_id=f"event:{uuid.uuid4().hex[:12]}",
            event_type="approval.timeout",
            occurred_at=datetime.now(UTC),
            session_id=raw.get("session_id"),
            channel=raw.get("channel"),
            payload={
                "approvalId": raw.get("approval_id"),
                "sessionId": raw.get("session_id"),
            },
        )

    if raw_type == "error":
        return RuntimeEvent(
            event_id=f"event:{uuid.uuid4().hex[:12]}",
            event_type="error",
            occurred_at=datetime.now(UTC),
            session_id=raw.get("session_id"),
            channel=raw.get("channel"),
            payload={
                "message": raw.get("message", "Unknown runtime error"),
            },
        )

    if raw_type == "intent:update":
        return RuntimeEvent(
            event_id=f"event:{uuid.uuid4().hex[:12]}",
            event_type="intent.update",
            occurred_at=datetime.now(UTC),
            session_id=raw.get("session_id"),
            payload={
                "sessionId": raw.get("session_id"),
                "graph": raw.get("graph", {}),
            },
        )

    return None

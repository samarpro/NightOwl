"""HITL approval gate.

Creates ApprovalRequests, broadcasts via WebSocket, sends to the user's last
messaging channel (inline keyboard), and waits on an asyncio.Event with timeout.
First response wins.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from nightowl.channels.outbound import ChannelDeliveryService
from nightowl.channels.types import ChannelTarget
from nightowl.config import settings
from nightowl.models.approval import ApprovalRequest, RiskLevel
from nightowl.sessions.manager import SessionManager

log = logging.getLogger(__name__)


class HITLGate:
    def __init__(
        self,
        manager: SessionManager,
        event_bus: Any | None = None,
        timeout_seconds: float | None = None,
        outbound_service: ChannelDeliveryService | None = None,
    ) -> None:
        self._manager = manager
        self._event_bus = event_bus
        self._outbound_service = outbound_service
        self._timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else settings.hitl_timeout_seconds
        )
        # approval_id -> (asyncio.Event, result dict)
        self._pending: dict[str, tuple[asyncio.Event, dict[str, Any]]] = {}
        self._channels: dict[str, ChannelTarget] = {}

    def set_last_channel(self, session_id: str, channel: str, chat_id: str) -> None:
        """Record the last messaging channel for a session."""
        self._channels[session_id] = ChannelTarget(channel=channel, chat_id=chat_id)

    def set_last_channel_target(self, session_id: str, target: ChannelTarget) -> None:
        self._channels[session_id] = target

    async def _broadcast_event(self, event: dict[str, Any]) -> None:
        if self._event_bus is not None:
            await self._event_bus.publish(event)

    async def _send_channel_approval(
        self,
        approval_id: str,
        session_id: str,
        tool_name: str,
        tool_args: dict[str, Any],
        risk_level: RiskLevel,
    ) -> None:
        if self._outbound_service is None:
            log.info("No outbound service configured for approval %s", approval_id)
            return
        await self._outbound_service.send_approval_request(
            session_id=session_id,
            approval_id=approval_id,
            tool_name=tool_name,
            tool_args=tool_args,
            risk_level=risk_level,
        )

    async def request_approval(
        self,
        session_id: str,
        tool_name: str,
        tool_args: dict[str, Any],
        risk_level: RiskLevel,
    ) -> bool:
        """Request human approval for a tool call.

        Broadcasts an approval:required event via WebSocket, sends to the
        user's last channel if available, then blocks until resolved or timeout.
        Returns True if approved, False if rejected or timed out.
        """
        approval_id = f"approval:{uuid.uuid4().hex[:12]}"
        event = asyncio.Event()
        expires_at = datetime.now(UTC) + timedelta(seconds=self._timeout_seconds)
        channel_info = self._channels.get(session_id)
        result: dict[str, Any] = {
            "approved": False,
            "reason": None,
            "session_id": session_id,
            "channel": channel_info.channel if channel_info else None,
        }
        self._pending[approval_id] = (event, result)

        # Broadcast to dashboard via WebSocket
        await self._broadcast_event({
            "type": "approval:required",
            "approval_id": approval_id,
            "session_id": session_id,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "risk_level": risk_level,
            "channel": channel_info.channel if channel_info else None,
            "expires_at": expires_at.isoformat(),
        })

        # Send to user's last messaging channel if available
        if channel_info:
            await self._send_channel_approval(
                approval_id=approval_id,
                session_id=session_id,
                tool_name=tool_name,
                tool_args=tool_args,
                risk_level=risk_level,
            )

        # Wait for resolution or timeout
        try:
            await asyncio.wait_for(event.wait(), timeout=self._timeout_seconds)
        except asyncio.TimeoutError:
            log.warning("Approval %s timed out after %.1fs", approval_id, self._timeout_seconds)
            await self._broadcast_event({
                "type": "approval:timeout",
                "approval_id": approval_id,
                "session_id": session_id,
                "channel": channel_info.channel if channel_info else None,
            })
            self._pending.pop(approval_id, None)
            return False

        approved = result["approved"]
        self._pending.pop(approval_id, None)
        return approved

    def resolve_approval(
        self,
        approval_id: str,
        approved: bool,
        reason: str | None = None,
    ) -> None:
        """Resolve a pending approval. First response wins."""
        pending = self._pending.get(approval_id)
        if pending is None:
            log.debug("Approval %s not found or already resolved", approval_id)
            return

        event, result = pending
        if event.is_set():
            # Already resolved — first response wins
            return

        result["approved"] = approved
        result["reason"] = reason
        event.set()

        # Fire-and-forget broadcast of resolution
        asyncio.ensure_future(self._broadcast_event({
            "type": "approval:resolved",
            "approval_id": approval_id,
            "session_id": result.get("session_id"),
            "channel": result.get("channel"),
            "approved": approved,
            "reason": reason,
        }))

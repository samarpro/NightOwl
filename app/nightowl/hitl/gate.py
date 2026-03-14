"""HITL approval gate.

Creates ApprovalRequests, broadcasts via WebSocket, sends to the user's last
messaging channel (inline keyboard), and waits on an asyncio.Event with timeout.
First response wins.
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from nightowl.config import settings
from nightowl.models.approval import ApprovalDecision, ApprovalRequest, ApprovalResult, RiskLevel
from nightowl.sessions.manager import SessionManager

log = logging.getLogger(__name__)


class HITLGate:
    def __init__(
        self,
        manager: SessionManager,
        event_bus: Any | None = None,
        timeout_seconds: float | None = None,
        registry: Any | None = None,
    ) -> None:
        self._manager = manager
        self._event_bus = event_bus
        self._registry = registry
        self._timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else settings.hitl_timeout_seconds
        )
        # approval_id -> (asyncio.Event, result dict)
        self._pending: dict[str, tuple[asyncio.Event, dict[str, Any]]] = {}
        # session_id -> channel info
        self._channels: dict[str, dict[str, str]] = {}
        # session_id -> redirect wait state
        self._pending_redirects: dict[str, dict[str, Any]] = {}

    def set_last_channel(self, session_id: str, channel: str, chat_id: str) -> None:
        """Record the last messaging channel for a session."""
        self._channels[session_id] = {"channel": channel, "chat_id": chat_id}

    def _resolve_channel(self, session_id: str) -> dict[str, str] | None:
        """Find channel info for a session, walking up the parent chain if needed."""
        info = self._channels.get(session_id)
        if info:
            return info
        # Walk up to parent — child sessions inherit the main session's channel
        session = self._manager.get_session(session_id)
        while session and session.parent_id:
            info = self._channels.get(session.parent_id)
            if info:
                return info
            session = self._manager.get_session(session.parent_id)
        return None

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
        reason: str = "",
    ) -> dict[str, str] | None:
        if self._registry is None:
            log.info("No channel registry configured for approval %s", approval_id)
            return None
        channel_info = self._resolve_channel(session_id)
        if not channel_info:
            return None
        bridge = self._registry.get(channel_info["channel"])
        if bridge is None:
            return None
        approval = ApprovalRequest(
            id=approval_id,
            session_id=session_id,
            tool_name=tool_name,
            tool_args=tool_args,
            risk_level=risk_level,
            reason=reason,
        )
        return await bridge.send_approval_request(channel_info["chat_id"], approval)

    async def _send_redirect_prompt(
        self,
        session_id: str,
        tool_name: str,
        *,
        reply_to_message_id: str | None = None,
    ) -> None:
        if self._registry is None:
            return
        channel_info = self._resolve_channel(session_id)
        if not channel_info:
            return
        bridge = self._registry.get(channel_info["channel"])
        if bridge is None:
            return
        await bridge.send_message(
            channel_info["chat_id"],
            (
                f"Redirect noted for `{tool_name}`. Reply with the new direction you want me "
                "to follow, and I will continue from that instead of the blocked action."
            ),
            reply_to_message_id=reply_to_message_id,
        )

    async def request_approval(
        self,
        session_id: str,
        tool_name: str,
        tool_args: dict[str, Any],
        risk_level: RiskLevel,
        reason: str = "",
    ) -> ApprovalResult:
        """Request human approval for a tool call.

        Broadcasts an approval:required event via WebSocket, sends to the
        user's last channel if available, then blocks until resolved or timeout.
        Returns an ApprovalResult describing the user's decision.
        """
        approval_id = f"approval:{uuid.uuid4().hex[:12]}"
        event = asyncio.Event()
        channel_info = self._resolve_channel(session_id)
        result: dict[str, Any] = {
            "decision": ApprovalDecision.REJECT,
            "reason": None,
            "redirect_message": None,
            "session_id": session_id,
            "tool_name": tool_name,
            "channel": channel_info["channel"] if channel_info else None,
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
            "reason": reason,
            "channel": channel_info["channel"] if channel_info else None,
        })

        # Send to user's last messaging channel if available
        if channel_info:
            channel_message_ref = await self._send_channel_approval(
                approval_id=approval_id,
                session_id=session_id,
                tool_name=tool_name,
                tool_args=tool_args,
                risk_level=risk_level,
                reason=reason,
            )
            if channel_message_ref:
                result["approval_message_ref"] = channel_message_ref

        # Wait indefinitely for the human to respond
        await event.wait()

        decision = ApprovalResult(
            decision=result["decision"],
            reason=result["reason"],
            redirect_message=result["redirect_message"],
        )
        self._pending.pop(approval_id, None)
        return decision

    def resolve_approval(
        self,
        approval_id: str,
        decision: ApprovalDecision,
        reason: str | None = None,
        redirect_message: str | None = None,
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

        result["decision"] = decision
        result["reason"] = reason
        result["redirect_message"] = redirect_message
        event.set()

        if decision == ApprovalDecision.REDIRECT:
            approval_ref = result.get("approval_message_ref") or {}
            self._pending_redirects[result["session_id"]] = {
                "approval_id": approval_id,
                "tool_name": result.get("tool_name"),
                "reason": reason,
                "reply_to_message_id": approval_ref.get("message_id"),
            }
            asyncio.ensure_future(self._send_redirect_prompt(
                result["session_id"],
                tool_name=result.get("tool_name") or "the blocked action",
                reply_to_message_id=approval_ref.get("message_id"),
            ))

        # Fire-and-forget broadcast of resolution
        asyncio.ensure_future(self._broadcast_event({
            "type": "approval:resolved",
            "approval_id": approval_id,
            "session_id": result.get("session_id"),
            "channel": result.get("channel"),
            "decision": decision,
            "reason": reason,
            "redirect_message": redirect_message,
        }))

    def consume_redirect_instruction(self, session_id: str, text: str) -> str | None:
        redirect_state = self._pending_redirects.pop(session_id, None)
        if redirect_state is None:
            return None
        tool_name = redirect_state.get("tool_name", "the blocked tool")
        return (
            "[SYSTEM: USER REDIRECTED A BLOCKED ACTION]\n"
            f"The user rejected executing `{tool_name}` and has now provided a new direction.\n"
            "Do not continue with the blocked action unless the user explicitly asks again.\n"
            "Treat the following as the user's updated instruction and continue from there:\n"
            f"{text}"
        )

    def handle_text_response(self, text: str) -> bool:
        match = re.match(r"^\s*(approve|reject|redirect)\s+(approval:[^\s:]+)\s*$", text, re.IGNORECASE)
        if not match:
            return False

        verb, approval_id = match.groups()
        if approval_id not in self._pending:
            return False
        decision = ApprovalDecision(verb.lower())
        reason = {
            ApprovalDecision.APPROVE: "Approved via channel message",
            ApprovalDecision.REJECT: "Rejected via channel message",
            ApprovalDecision.REDIRECT: "Redirected via channel message",
        }[decision]
        self.resolve_approval(approval_id, decision=decision, reason=reason)
        return True

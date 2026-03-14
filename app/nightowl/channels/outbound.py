"""Outbound reply and approval delivery."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from nightowl.channels.registry import ChannelRegistry
from nightowl.channels.session_routing import ChannelSessionRouter
from nightowl.models.approval import RiskLevel


class ChannelDeliveryService:
    def __init__(
        self,
        routing: ChannelSessionRouter,
        registry: ChannelRegistry,
        emit: Callable[[dict[str, object]], Awaitable[None]],
    ) -> None:
        self._routing = routing
        self._registry = registry
        self._emit = emit

    async def send_reply(self, session_id: str, text: str) -> None:
        target = self._routing.get_target(session_id)
        if target is None:
            return
        adapter = self._registry.get_outbound(target.channel)
        if adapter is None:
            await self._emit({
                "type": "channel:reply_failed",
                "session_id": session_id,
                "channel": target.channel,
                "chat_id": target.chat_id,
                "text": text,
                "error": f"No outbound adapter for {target.channel}",
            })
            return

        await self._emit({
            "type": "channel:reply_queued",
            "session_id": session_id,
            "channel": target.channel,
            "chat_id": target.chat_id,
            "text": text,
        })
        result = await adapter.send_text(target, text)
        if result.delivered:
            await self._emit({
                "type": "channel:reply_sent",
                "session_id": session_id,
                "channel": target.channel,
                "chat_id": target.chat_id,
                "text": text,
                "message_id": result.provider_message_id,
            })
            return

        await self._emit({
            "type": "channel:reply_failed",
            "session_id": session_id,
            "channel": target.channel,
            "chat_id": target.chat_id,
            "text": text,
            "error": result.error,
        })

    async def send_approval_request(
        self,
        session_id: str,
        approval_id: str,
        tool_name: str,
        tool_args: dict[str, object],
        risk_level: RiskLevel,
    ) -> None:
        text = (
            f"Approval required for {tool_name}\n"
            f"Risk: {risk_level.value}\n"
            f"Approval ID: {approval_id}\n"
            f"Args: {tool_args}"
        )
        await self.send_reply(session_id, text)

"""WhatsApp channel bridge using Twilio WhatsApp Business API."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from nightowl.channels.base import ChannelBridge
from nightowl.channels.formatting import markdown_to_whatsapp
from nightowl.models.approval import ApprovalRequest
from nightowl.models.message import ChannelMessage


def _get_twilio_client():
    from twilio.rest import Client
    from nightowl.config import settings
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def _get_twilio_from_number() -> str:
    from nightowl.config import settings
    return settings.twilio_phone_number


class WhatsAppBridge(ChannelBridge):
    """Bridge for WhatsApp via Twilio."""

    channel_id = "whatsapp"

    def __init__(self) -> None:
        self._client = _get_twilio_client()
        self._from_number = _get_twilio_from_number()

    async def start(self) -> None:
        pass

    def normalize_inbound(self, raw: dict[str, Any]) -> ChannelMessage:
        from_field = raw["From"]
        # Strip whatsapp: prefix
        sender_id = from_field.removeprefix("whatsapp:")
        text = raw.get("Body", "")
        return ChannelMessage(
            channel=self.channel_id,
            sender_id=sender_id,
            text=text,
            thread_id=None,
        )

    async def send_message(
        self,
        user_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,
    ) -> None:
        formatted = markdown_to_whatsapp(text)
        to = f"whatsapp:{user_id}" if not user_id.startswith("whatsapp:") else user_id
        from_ = f"whatsapp:{self._from_number}" if not self._from_number.startswith("whatsapp:") else self._from_number
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.messages.create(to=to, from_=from_, body=formatted),
        )

    async def send_approval_request(self, user_id: str, approval: ApprovalRequest) -> dict[str, str] | None:
        text = (
            f"Approval Required [{approval.risk_level.value.upper()}]\n\n"
            f"Tool: {approval.tool_name}\n"
            f"Args: {json.dumps(approval.tool_args)}\n"
            f"Session: {approval.session_id}\n"
            f"ID: {approval.id}\n\n"
            f"Reply APPROVE {approval.id}, REJECT {approval.id}, or REDIRECT {approval.id}"
        )
        to = f"whatsapp:{user_id}" if not user_id.startswith("whatsapp:") else user_id
        from_ = f"whatsapp:{self._from_number}" if not self._from_number.startswith("whatsapp:") else self._from_number
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.messages.create(to=to, from_=from_, body=text),
        )
        return None

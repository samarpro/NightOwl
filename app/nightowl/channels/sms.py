"""SMS channel bridge using Twilio SMS API."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from nightowl.channels.base import ChannelBridge
from nightowl.models.approval import ApprovalRequest
from nightowl.models.message import ChannelMessage


def _get_twilio_client():
    from twilio.rest import Client
    from nightowl.config import settings
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def _get_twilio_from_number() -> str:
    from nightowl.config import settings
    return settings.twilio_phone_number


class SMSBridge(ChannelBridge):
    """Bridge for SMS via Twilio."""

    channel_id = "sms"

    def __init__(self) -> None:
        self._client = _get_twilio_client()
        self._from_number = _get_twilio_from_number()

    async def start(self) -> None:
        pass

    def normalize_inbound(self, raw: dict[str, Any]) -> ChannelMessage:
        sender_id = raw["From"]
        text = raw.get("Body", "")
        return ChannelMessage(
            channel=self.channel_id,
            sender_id=sender_id,
            text=text,
            thread_id=None,
        )

    async def send_message(self, user_id: str, text: str) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.messages.create(
                to=user_id, from_=self._from_number, body=text,
            ),
        )

    async def send_approval_request(self, user_id: str, approval: ApprovalRequest) -> None:
        text = (
            f"Approval Required [{approval.risk_level.value.upper()}]\n\n"
            f"Tool: {approval.tool_name}\n"
            f"Args: {json.dumps(approval.tool_args)}\n"
            f"Session: {approval.session_id}\n"
            f"ID: {approval.id}\n\n"
            f"Reply APPROVE {approval.id} or REJECT {approval.id}"
        )
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.messages.create(
                to=user_id, from_=self._from_number, body=text,
            ),
        )

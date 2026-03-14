"""Telegram channel bridge using python-telegram-bot."""

from __future__ import annotations

import json
from typing import Any

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from nightowl.channels.base import ChannelBridge
from nightowl.models.approval import ApprovalRequest
from nightowl.models.message import ChannelMessage


def _get_bot_token() -> str:
    from nightowl.config import settings
    return settings.telegram_bot_token


class TelegramBridge(ChannelBridge):
    """Bridge for Telegram Bot API."""

    channel_id = "telegram"

    def __init__(self) -> None:
        token = _get_bot_token()
        self._bot = Bot(token=token)

    async def start(self) -> None:
        pass

    def normalize_inbound(self, raw: dict[str, Any]) -> ChannelMessage:
        sender_id = str(raw["from"]["id"])
        text = raw.get("text", "")
        thread_id = raw.get("message_thread_id")
        return ChannelMessage(
            channel=self.channel_id,
            sender_id=sender_id,
            text=text,
            thread_id=str(thread_id) if thread_id is not None else None,
        )

    async def send_message(self, user_id: str, text: str) -> None:
        await self._bot.send_message(chat_id=user_id, text=text)

    async def send_approval_request(self, user_id: str, approval: ApprovalRequest) -> None:
        text = (
            f"🔒 Approval Required [{approval.risk_level.value.upper()}]\n\n"
            f"Tool: {approval.tool_name}\n"
            f"Args: {json.dumps(approval.tool_args)}\n"
            f"Session: {approval.session_id}"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve:{approval.id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject:{approval.id}"),
            ]
        ])
        await self._bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=keyboard,
        )

"""Telegram channel bridge using python-telegram-bot."""

from __future__ import annotations

import json
from typing import Any

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from nightowl.channels.base import ChannelBridge
from nightowl.channels.formatting import markdown_to_telegram_html
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

    async def send_message(
        self,
        user_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,
    ) -> None:
        html = markdown_to_telegram_html(text)
        kwargs: dict[str, Any] = {
            "chat_id": user_id,
            "text": html,
            "parse_mode": "HTML",
        }
        if reply_to_message_id is not None:
            kwargs["reply_to_message_id"] = int(reply_to_message_id)
        await self._bot.send_message(**kwargs)

    async def send_approval_request(self, user_id: str, approval: ApprovalRequest) -> dict[str, str] | None:
        args_str = json.dumps(approval.tool_args, indent=2)
        reason_line = f"\n<b>Why:</b> {approval.reason}" if approval.reason else ""
        text = (
            f"🔒 <b>Approval Required</b> [{approval.risk_level.value.upper()}]\n\n"
            f"<b>Tool:</b> <code>{approval.tool_name}</code>\n"
            f"<b>Args:</b>\n<pre>{args_str}</pre>"
            f"{reason_line}"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve:{approval.id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject:{approval.id}"),
                InlineKeyboardButton("↩ Redirect", callback_data=f"redirect:{approval.id}"),
            ]
        ])
        sent = await self._bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return {"message_id": str(sent.message_id)}

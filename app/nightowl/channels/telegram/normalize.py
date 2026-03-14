"""Normalize Telegram webhook payloads into ChannelMessage."""

from __future__ import annotations

from datetime import UTC, datetime

from nightowl.channels.telegram.schemas import TelegramUpdate
from nightowl.models.message import ChannelMessage


def normalize_telegram_update(update: TelegramUpdate) -> ChannelMessage | None:
    message = update.message
    if message is None or not message.text or message.from_ is None:
        return None

    display_name = message.from_.username or message.from_.first_name
    metadata = {"chat_type": message.chat.type}
    if update.update_id is not None:
        metadata["update_id"] = str(update.update_id)

    return ChannelMessage(
        channel="telegram",
        sender_id=str(message.from_.id),
        sender_display_name=display_name,
        chat_id=str(message.chat.id),
        thread_id=str(message.message_thread_id) if message.message_thread_id is not None else None,
        message_id=str(message.message_id),
        text=message.text,
        received_at=datetime.now(UTC),
        metadata=metadata,
    )

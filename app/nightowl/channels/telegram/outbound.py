"""Telegram outbound adapter."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from nightowl.channels.types import ChannelTarget, DeliveryResult
from nightowl.config import settings


async def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    def _send() -> dict[str, Any]:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    return await asyncio.to_thread(_send)


class TelegramOutbound:
    def __init__(self, bot_token: str | None = None) -> None:
        self._bot_token = bot_token or settings.telegram_bot_token

    async def send_text(self, target: ChannelTarget, text: str) -> DeliveryResult:
        if not self._bot_token:
            return DeliveryResult(delivered=False, error="Missing Telegram bot token")

        payload: dict[str, Any] = {
            "chat_id": target.chat_id,
            "text": text,
        }
        if target.thread_id:
            payload["message_thread_id"] = int(target.thread_id)
        if target.message_id:
            payload["reply_to_message_id"] = int(target.message_id)

        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        try:
            result = await _post_json(url, payload)
        except (HTTPError, URLError, ValueError) as exc:
            return DeliveryResult(delivered=False, error=str(exc))

        if not result.get("ok"):
            return DeliveryResult(delivered=False, error=str(result.get("description", "unknown error")))

        message = result.get("result", {})
        return DeliveryResult(
            delivered=True,
            provider_message_id=str(message.get("message_id")) if message.get("message_id") is not None else None,
        )

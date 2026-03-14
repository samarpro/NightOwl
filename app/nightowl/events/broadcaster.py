"""In-memory broadcaster for websocket subscribers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from nightowl.events.translate import translate_runtime_event

log = logging.getLogger(__name__)


class RuntimeBroadcaster:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

    async def publish(self, event: dict[str, Any]) -> None:
        translated = translate_runtime_event(event)
        if translated is None:
            return
        payload = translated.model_dump(mode="json")
        for queue in list(self._subscribers):
            await queue.put(payload)

    async def subscribe(self) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)


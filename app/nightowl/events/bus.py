"""Redis pub/sub event bus."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as aioredis

from nightowl.config import settings

log = logging.getLogger(__name__)

CHANNEL = "nightowl:events"


class EventBus:
    def __init__(self, redis_url: str | None = None) -> None:
        self._url = redis_url or settings.redis_url
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._redis = aioredis.from_url(self._url, decode_responses=True)
        await self._redis.ping()
        log.info("EventBus connected to %s", self._url)

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    async def publish(self, event: dict[str, Any]) -> None:
        if self._redis is None:
            log.warning("EventBus not connected, dropping event: %s", event.get("type"))
            return
        await self._redis.publish(CHANNEL, json.dumps(event, default=str))

    async def subscribe(
        self, types: set[str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        if self._redis is None:
            raise RuntimeError("EventBus not connected")

        pubsub = self._redis.pubsub()
        await pubsub.subscribe(CHANNEL)
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    event = json.loads(message["data"])
                except (json.JSONDecodeError, TypeError):
                    continue
                if types and event.get("type") not in types:
                    continue
                yield event
        finally:
            await pubsub.unsubscribe(CHANNEL)
            await pubsub.aclose()

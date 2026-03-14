"""Shared test fixtures for NightOwl test suite."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

from nightowl.sessions.manager import SessionManager


class FakeEventBus:
    """In-memory event bus for tests — same interface as EventBus."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def publish(self, event: dict[str, Any]) -> None:
        serialised = json.loads(json.dumps(event, default=str))
        await self._queue.put(serialised)

    async def subscribe(self, types: set[str] | None = None) -> AsyncIterator[dict[str, Any]]:
        while True:
            event = await self._queue.get()
            if types and event.get("type") not in types:
                continue
            yield event

    def get_nowait(self) -> dict[str, Any] | None:
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def drain(self) -> list[dict[str, Any]]:
        events = []
        while not self._queue.empty():
            events.append(self._queue.get_nowait())
        return events

    @property
    def empty(self) -> bool:
        return self._queue.empty()


@pytest.fixture
def manager() -> SessionManager:
    return SessionManager()


@pytest.fixture
def fake_bus() -> FakeEventBus:
    return FakeEventBus()


@pytest.fixture
def manager_with_broadcast(fake_bus: FakeEventBus) -> tuple[SessionManager, FakeEventBus]:
    m = SessionManager()
    m.set_event_bus(fake_bus)
    return m, fake_bus

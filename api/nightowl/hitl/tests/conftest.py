"""Shared fixtures for HITL tests."""

from __future__ import annotations

import asyncio

import pytest

from nightowl.sessions.manager import SessionManager


@pytest.fixture
def manager() -> SessionManager:
    return SessionManager()


@pytest.fixture
def manager_with_broadcast() -> tuple[SessionManager, asyncio.Queue]:
    m = SessionManager()
    q: asyncio.Queue = asyncio.Queue()
    m.set_broadcast_queue(q)
    return m, q

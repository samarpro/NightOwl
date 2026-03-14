"""Shared fixtures for sandbox tests."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from nightowl.sessions.manager import SessionManager
from nightowl.sessions.tools import AgentState


@pytest.fixture
def manager() -> SessionManager:
    return SessionManager()


@dataclass
class _FakeCtx:
    deps: AgentState


@pytest.fixture
async def ctx_with_manager(manager: SessionManager) -> _FakeCtx:
    session = await manager.create_main_session("test")
    state = AgentState(session_id=session.id, manager=manager)
    return _FakeCtx(deps=state)

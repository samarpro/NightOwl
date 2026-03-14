"""Shared fixtures for Composio meta-tools tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from nightowl.sessions.manager import SessionManager
from nightowl.sessions.tools import AgentState


@dataclass
class _FakeCtx:
    """Minimal stand-in for RunContext — only .deps is accessed by tools."""

    deps: AgentState


@pytest.fixture
def manager() -> SessionManager:
    return SessionManager()


@pytest.fixture
def fake_composio_client() -> MagicMock:
    """A mock Composio client with search and execute stubs."""
    client = MagicMock()
    client.search_tools = AsyncMock(return_value=[
        {"name": "GOOGLECALENDAR_LIST_EVENTS", "description": "List Google Calendar events"},
        {"name": "GOOGLECALENDAR_CREATE_EVENT", "description": "Create a Google Calendar event"},
    ])
    client.execute_tool = AsyncMock(return_value={"status": "ok", "data": {"event_id": "evt_123"}})
    return client


@pytest.fixture
async def agent_state(manager: SessionManager, fake_composio_client: MagicMock) -> AgentState:
    session = await manager.create_main_session("test task")
    state = AgentState(session_id=session.id, manager=manager)
    return state


@pytest.fixture
def ctx(agent_state: AgentState) -> _FakeCtx:
    return _FakeCtx(deps=agent_state)

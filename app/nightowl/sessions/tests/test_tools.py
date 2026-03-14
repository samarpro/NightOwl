"""Tests for session tool functions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from nightowl.models.session import SpawnRequest
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.tools import AgentState, sessions_list, sessions_send, sessions_spawn


@dataclass
class _FakeCtx:
    """Minimal stand-in for RunContext — only .deps is accessed by the tools."""

    deps: AgentState


def _make_ctx(session_id: str, manager: SessionManager) -> _FakeCtx:
    return _FakeCtx(deps=AgentState(session_id=session_id, manager=manager))


class TestSessionsSpawn:
    async def test_spawn_returns_child_id_and_no_poll_instruction(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        ctx = _make_ctx(parent.id, manager)
        result = await sessions_spawn(ctx, task="find restaurants")
        assert "do NOT poll" in result
        assert "session:" in result

    async def test_spawn_creates_child_on_manager(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        ctx = _make_ctx(parent.id, manager)
        await sessions_spawn(ctx, task="search", label="search-agent")
        children = manager.list_children(parent.id)
        assert len(children) == 1
        assert children[0].label == "search-agent"

    async def test_spawn_with_sandbox_mode(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        ctx = _make_ctx(parent.id, manager)
        await sessions_spawn(ctx, task="browse", sandbox="browser")
        children = manager.list_children(parent.id)
        assert children[0].sandbox_mode.value == "browser"


class TestSessionsList:
    async def test_list_returns_empty_when_no_children(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        ctx = _make_ctx(parent.id, manager)
        result = await sessions_list(ctx)
        assert result == []

    async def test_list_returns_all_children_with_status(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        ctx = _make_ctx(parent.id, manager)
        await sessions_spawn(ctx, task="task a", label="a")
        await sessions_spawn(ctx, task="task b", label="b")
        result = await sessions_list(ctx)
        assert len(result) == 2
        labels = {r["label"] for r in result}
        assert labels == {"a", "b"}
        # Each entry has the expected keys
        for entry in result:
            assert "id" in entry
            assert "role" in entry
            assert "state" in entry
            assert "task" in entry


class TestSessionsSend:
    async def test_send_to_own_child_succeeds(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(parent.id, SpawnRequest(task="work"))
        ctx = _make_ctx(parent.id, manager)
        result = await sessions_send(ctx, child.id, "update your approach")
        assert "sent" in result.lower()

    async def test_send_to_nonexistent_session_returns_not_found(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        ctx = _make_ctx(parent.id, manager)
        result = await sessions_send(ctx, "session:doesnotexist", "hello")
        assert "not found" in result.lower()

    async def test_send_to_non_child_session_rejected(self, manager: SessionManager):
        p1 = await manager.create_main_session("parent 1")
        p2 = await manager.create_main_session("parent 2")
        child_of_p2 = await manager.spawn_child(p2.id, SpawnRequest(task="work"))
        ctx = _make_ctx(p1.id, manager)
        result = await sessions_send(ctx, child_of_p2.id, "sneaky message")
        assert "not your child" in result.lower()

    async def test_sent_message_arrives_on_child_queue(self, manager: SessionManager):
        import asyncio

        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(parent.id, SpawnRequest(task="work"))
        ctx = _make_ctx(parent.id, manager)
        await sessions_send(ctx, child.id, "change direction")

        q = manager.get_queue(child.id)
        msg = await asyncio.wait_for(q.get(), timeout=1)
        assert msg == "change direction"

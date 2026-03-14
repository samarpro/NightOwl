"""Tests for slash command handling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from nightowl.ingest.commands import CommandResult, handle_command
from nightowl.models.session import Session, SessionRole, SessionState
from nightowl.sessions.manager import SessionManager


@dataclass
class _FakeWorkerState:
    runtime: Any
    task: Any


class _FakeRuntime:
    def __init__(self):
        self.message_history = [{"role": "user", "content": "hello"}] * 5
        self.persisted_count = 5


class TestCommandParsing:
    async def test_non_command_returns_none(self, manager: SessionManager):
        result = await handle_command("hello there", "session:1", manager, {})
        assert result is None

    async def test_unknown_command_returns_none(self, manager: SessionManager):
        result = await handle_command("/frobnicate", "session:1", manager, {})
        assert result is None

    async def test_command_is_case_insensitive(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        result = await handle_command("/HELP", session.id, manager, {})
        assert result is not None
        assert "Available commands" in result.reply

    async def test_command_with_leading_whitespace(self, manager: SessionManager):
        result = await handle_command("  /help", "session:1", manager, {})
        assert result is not None


class TestClear:
    async def test_clear_resets_runtime_history(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        runtime = _FakeRuntime()
        workers = {session.id: _FakeWorkerState(runtime=runtime, task=MagicMock())}

        result = await handle_command("/clear", session.id, manager, workers)

        assert result is not None
        assert "cleared" in result.reply.lower()
        assert runtime.message_history == []
        assert runtime.persisted_count == 0

    async def test_clear_calls_store_clear_messages(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        manager.store = MagicMock()
        manager.store.clear_messages = AsyncMock(return_value=5)

        result = await handle_command("/clear", session.id, manager, {})

        assert result is not None
        manager.store.clear_messages.assert_called_once_with(session.id)

    async def test_clear_does_not_end_session(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        result = await handle_command("/clear", session.id, manager, {})
        assert result.end_session is False

    async def test_clear_completes_child_sessions(self, manager: SessionManager):
        from nightowl.models.session import SpawnRequest

        session = await manager.create_main_session("test")
        child = await manager.spawn_child(session.id, SpawnRequest(task="sub-task", label="child-1"))

        await handle_command("/clear", session.id, manager, {})

        assert child.state == SessionState.COMPLETED
        assert session.children == []
        assert session.expected_completions == set()

    async def test_clear_completes_nested_children(self, manager: SessionManager):
        from nightowl.models.session import SpawnRequest

        session = await manager.create_main_session("test")
        child = await manager.spawn_child(session.id, SpawnRequest(task="orch", label="orch"))
        grandchild = await manager.spawn_child(child.id, SpawnRequest(task="leaf", label="leaf"))

        await handle_command("/clear", session.id, manager, {})

        assert grandchild.state == SessionState.COMPLETED
        assert child.state == SessionState.COMPLETED

    async def test_clear_emits_session_cleared_event(self, manager: SessionManager):
        from nightowl.sessions.tests.conftest import FakeEventBus

        bus = FakeEventBus()
        manager.set_event_bus(bus)
        session = await manager.create_main_session("test")
        bus.drain()  # discard session:created event

        await handle_command("/clear", session.id, manager, {})

        events = bus.drain()
        cleared = [e for e in events if e.get("type") == "session:cleared"]
        assert len(cleared) == 1
        assert cleared[0]["session_id"] == session.id


class TestNew:
    async def test_new_ends_session(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        task_mock = MagicMock()
        workers = {session.id: _FakeWorkerState(runtime=_FakeRuntime(), task=task_mock)}

        result = await handle_command("/new", session.id, manager, workers)

        assert result is not None
        assert result.end_session is True
        assert session.id not in workers
        task_mock.cancel.assert_called_once()

    async def test_new_completes_session_in_manager(self, manager: SessionManager):
        session = await manager.create_main_session("test")

        await handle_command("/new", session.id, manager, {})

        updated = manager.get_session(session.id)
        assert updated.state == SessionState.COMPLETED


class TestStatus:
    async def test_status_shows_session_info(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        result = await handle_command("/status", session.id, manager, {})

        assert result is not None
        assert session.id in result.reply
        assert "running" in result.reply.lower()

    async def test_status_shows_children(self, manager: SessionManager):
        from nightowl.models.session import SpawnRequest

        session = await manager.create_main_session("test")
        await manager.spawn_child(session.id, SpawnRequest(task="sub-task", label="research-child"))

        result = await handle_command("/status", session.id, manager, {})

        assert "research-child" in result.reply

    async def test_status_no_session(self, manager: SessionManager):
        result = await handle_command("/status", "session:nonexistent", manager, {})
        assert "no active session" in result.reply.lower()


class TestHelp:
    async def test_help_lists_commands(self, manager: SessionManager):
        result = await handle_command("/help", "session:1", manager, {})
        assert result is not None
        assert "/clear" in result.reply
        assert "/new" in result.reply
        assert "/status" in result.reply
        assert "/help" in result.reply

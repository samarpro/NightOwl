"""Unit tests for session runner — orchestration logic without Bedrock.

These tests mock pydantic_ai.Agent so they run without AWS credentials.
The live Bedrock integration is covered in test_integration.py.
"""

from __future__ import annotations

import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub out pydantic_ai (and its sub-modules used by runner.py) so the tests
# can run without the real package installed.
# ---------------------------------------------------------------------------
_pydantic_ai_stub = types.ModuleType("pydantic_ai")
_pydantic_ai_stub.Agent = MagicMock  # type: ignore[attr-defined]
_pydantic_ai_stub.RunContext = MagicMock  # type: ignore[attr-defined]
sys.modules.setdefault("pydantic_ai", _pydantic_ai_stub)

sys.modules.setdefault("pydantic_ai.models", types.ModuleType("pydantic_ai.models"))
_bedrock_model_stub = types.ModuleType("pydantic_ai.models.bedrock")
_bedrock_model_stub.BedrockConverseModel = MagicMock  # type: ignore[attr-defined]
sys.modules.setdefault("pydantic_ai.models.bedrock", _bedrock_model_stub)

sys.modules.setdefault("pydantic_ai.providers", types.ModuleType("pydantic_ai.providers"))
_bedrock_provider_stub = types.ModuleType("pydantic_ai.providers.bedrock")
_bedrock_provider_stub.BedrockProvider = MagicMock  # type: ignore[attr-defined]
sys.modules.setdefault("pydantic_ai.providers.bedrock", _bedrock_provider_stub)
# ---------------------------------------------------------------------------

from nightowl.models.session import SessionRole, SessionState, SpawnRequest  # noqa: E402
from nightowl.sessions.manager import SessionManager  # noqa: E402
from nightowl.sessions.runner import run_session  # noqa: E402


def _make_agent_result(output: str, messages: list | None = None) -> MagicMock:
    """Return a fake AgentRunResult with the given output."""
    result = MagicMock()
    result.output = output
    result.new_messages = MagicMock(return_value=messages or [])
    return result


@pytest.fixture
def manager() -> SessionManager:
    return SessionManager()


class TestRunSessionBasic:
    async def test_returns_agent_output(self, manager: SessionManager):
        """run_session returns the agent's text output."""
        session = await manager.create_main_session("Say hello")

        fake_result = _make_agent_result("Hello!")
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=fake_result)

        with patch("nightowl.sessions.runner._build_agent", return_value=mock_agent):
            response = await run_session(session, manager, "Say hello")

        assert response == "Hello!"

    async def test_session_marked_completed_after_run(self, manager: SessionManager):
        """Session state is COMPLETED when the run finishes successfully."""
        session = await manager.create_main_session("task")

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=_make_agent_result("done"))

        with patch("nightowl.sessions.runner._build_agent", return_value=mock_agent):
            await run_session(session, manager, "task")

        assert session.state == SessionState.COMPLETED

    async def test_session_result_stored(self, manager: SessionManager):
        """Session result is populated with the agent's response."""
        session = await manager.create_main_session("task")

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=_make_agent_result("my result"))

        with patch("nightowl.sessions.runner._build_agent", return_value=mock_agent):
            await run_session(session, manager, "task")

        assert session.result == "my result"

    async def test_initial_message_passed_to_agent(self, manager: SessionManager):
        """The initial_message argument is forwarded to the agent."""
        session = await manager.create_main_session("task")

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=_make_agent_result("ok"))

        with patch("nightowl.sessions.runner._build_agent", return_value=mock_agent):
            await run_session(session, manager, "do the thing now")

        call_args = mock_agent.run.call_args
        assert call_args.args[0] == "do the thing now"


class TestRunSessionWithChildren:
    async def test_enters_wait_loop_when_children_pending(self, manager: SessionManager):
        """When a child session is spawned, run_session waits for completions."""
        session = await manager.create_main_session("parent task")
        child = await manager.spawn_child(session.id, SpawnRequest(task="sub-task"))

        # First run returns some output; second run (after completion) gives the final answer
        first_result = _make_agent_result("spawned child, waiting", messages=["msg1"])
        second_result = _make_agent_result("final synthesis")

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=[first_result, second_result])

        async def deliver_completion():
            await asyncio.sleep(0)  # yield so run_session can enter wait loop
            await manager.complete_session(child.id, "child done")

        with patch("nightowl.sessions.runner._build_agent", return_value=mock_agent):
            # Deliver child completion concurrently so the wait loop can proceed
            _, response = await asyncio.gather(
                deliver_completion(),
                run_session(session, manager, "parent task"),
            )

        assert response == "final synthesis"
        assert mock_agent.run.call_count == 2

    async def test_session_state_is_waiting_before_completions(self, manager: SessionManager):
        """Session transitions to WAITING while pending child completions exist."""
        session = await manager.create_main_session("parent task")
        child = await manager.spawn_child(session.id, SpawnRequest(task="sub-task"))

        states_seen: list[SessionState] = []

        first_result = _make_agent_result("waiting for child")
        final_result = _make_agent_result("all done")

        original_emit = manager._emit

        async def capturing_emit(event: dict) -> None:
            await original_emit(event)
            if event.get("type") == "session:waiting":
                states_seen.append(SessionState.WAITING)

        manager._emit = capturing_emit  # type: ignore[method-assign]

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=[first_result, final_result])

        async def deliver():
            await asyncio.sleep(0)
            await manager.complete_session(child.id, "done")

        with patch("nightowl.sessions.runner._build_agent", return_value=mock_agent):
            await asyncio.gather(deliver(), run_session(session, manager, "task"))

        assert SessionState.WAITING in states_seen

    async def test_completion_message_forwarded_to_agent(self, manager: SessionManager):
        """The child completion message is passed to the agent in the second run."""
        session = await manager.create_main_session("parent task")
        child = await manager.spawn_child(session.id, SpawnRequest(task="sub-task", label="finder"))

        first_result = _make_agent_result("waiting", messages=["h1"])
        second_result = _make_agent_result("synthesised")

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=[first_result, second_result])

        async def deliver():
            await asyncio.sleep(0)
            await manager.complete_session(child.id, "found the data")

        with patch("nightowl.sessions.runner._build_agent", return_value=mock_agent):
            await asyncio.gather(deliver(), run_session(session, manager, "task"))

        second_call_args = mock_agent.run.call_args_list[1]
        completion_msg = second_call_args.args[0]
        assert "found the data" in completion_msg

    async def test_multiple_children_all_completions_required(self, manager: SessionManager):
        """run_session keeps waiting until ALL spawned children complete."""
        session = await manager.create_main_session("parent")
        c1 = await manager.spawn_child(session.id, SpawnRequest(task="a"))
        c2 = await manager.spawn_child(session.id, SpawnRequest(task="b"))

        results = [
            _make_agent_result("waiting", messages=[]),
            _make_agent_result("still waiting", messages=[]),
            _make_agent_result("all done"),
        ]
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=results)

        async def deliver():
            await asyncio.sleep(0)
            await manager.complete_session(c1.id, "done a")
            await asyncio.sleep(0)
            await manager.complete_session(c2.id, "done b")

        with patch("nightowl.sessions.runner._build_agent", return_value=mock_agent):
            _, response = await asyncio.gather(
                deliver(),
                run_session(session, manager, "parent"),
            )

        assert response == "all done"
        assert mock_agent.run.call_count == 3


class TestRunSessionStateTransitions:
    async def test_session_running_event_emitted(self, manager: SessionManager):
        """A session:running broadcast event is emitted when the session starts."""
        broadcast: asyncio.Queue = asyncio.Queue()
        manager.set_broadcast_queue(broadcast)

        session = await manager.create_main_session("task")
        # Drain the create event
        await broadcast.get()

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=_make_agent_result("done"))

        with patch("nightowl.sessions.runner._build_agent", return_value=mock_agent):
            await run_session(session, manager, "task")

        events = []
        while not broadcast.empty():
            events.append(await broadcast.get())

        event_types = [e["type"] for e in events]
        assert "session:running" in event_types

    async def test_session_completed_event_emitted(self, manager: SessionManager):
        """A session:completed broadcast event is emitted after the run finishes."""
        broadcast: asyncio.Queue = asyncio.Queue()
        manager.set_broadcast_queue(broadcast)

        session = await manager.create_main_session("task")
        await broadcast.get()  # drain create event

        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=_make_agent_result("done"))

        with patch("nightowl.sessions.runner._build_agent", return_value=mock_agent):
            await run_session(session, manager, "task")

        events = []
        while not broadcast.empty():
            events.append(await broadcast.get())

        event_types = [e["type"] for e in events]
        assert "session:completed" in event_types

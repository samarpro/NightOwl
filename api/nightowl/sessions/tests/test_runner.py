"""Unit tests for session runner — orchestration logic without Bedrock.

These tests mock _build_agent so no real LLM calls are made.  They verify:
- the agent is called with the right arguments
- session state transitions happen in the right order
- the spawn-and-wait loop works (wait, receive completion, re-run, exit)
- timeout handling exits the loop without crashing
- the final response is always passed to manager.complete_session()
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nightowl.models.session import SessionRole, SessionState, SpawnRequest
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.runner import run_session


# ── Helpers ────────────────────────────────────────────────────────────────


def _fake_result(output: str = "result text") -> MagicMock:
    """Minimal stand-in for a Pydantic AI AgentRunResult."""
    r = MagicMock()
    r.output = output
    r.new_messages = MagicMock(return_value=[])
    return r


def _mock_agent(output: str = "result text") -> MagicMock:
    """Agent mock whose .run() always returns a fixed result."""
    agent = MagicMock()
    agent.run = AsyncMock(return_value=_fake_result(output))
    return agent


@pytest.fixture
def manager() -> SessionManager:
    return SessionManager()


# ── Tests ──────────────────────────────────────────────────────────────────


class TestRunSessionBasic:
    async def test_returns_agent_output(self, manager: SessionManager):
        session = await manager.create_main_session("task")
        with patch("nightowl.sessions.runner._build_agent", return_value=_mock_agent("hello")):
            response = await run_session(session, manager, "hi")
        assert response == "hello"

    async def test_session_is_running_before_agent_call(self, manager: SessionManager):
        session = await manager.create_main_session("task")
        states_during_run: list[str] = []

        async def capture_state(*args, **kwargs):
            states_during_run.append(session.state)
            return _fake_result("done")

        mock = MagicMock()
        mock.run = capture_state

        with patch("nightowl.sessions.runner._build_agent", return_value=mock):
            await run_session(session, manager, "go")

        assert SessionState.RUNNING in states_during_run

    async def test_session_completed_after_run(self, manager: SessionManager):
        session = await manager.create_main_session("task")
        with patch("nightowl.sessions.runner._build_agent", return_value=_mock_agent("answer")):
            await run_session(session, manager, "go")
        assert session.state == SessionState.COMPLETED
        assert session.result == "answer"

    async def test_agent_called_with_initial_message(self, manager: SessionManager):
        session = await manager.create_main_session("task")
        mock = _mock_agent()
        with patch("nightowl.sessions.runner._build_agent", return_value=mock):
            await run_session(session, manager, "the initial message")
        call_args = mock.run.call_args_list[0]
        assert call_args.args[0] == "the initial message"

    async def test_skills_prompt_forwarded_to_prompt_builder(self, manager: SessionManager):
        session = await manager.create_main_session("task")
        with patch("nightowl.sessions.runner.build_system_prompt") as mock_build:
            mock_build.return_value = "system prompt"
            with patch("nightowl.sessions.runner._build_agent", return_value=_mock_agent()):
                await run_session(session, manager, "go", skills_prompt="can book tables")
        mock_build.assert_called_once_with(session, skills_prompt="can book tables")

    async def test_no_children_agent_called_exactly_once(self, manager: SessionManager):
        session = await manager.create_main_session("task")
        mock = _mock_agent()
        with patch("nightowl.sessions.runner._build_agent", return_value=mock):
            await run_session(session, manager, "go")
        assert mock.run.call_count == 1


class TestWaitLoop:
    async def test_enters_waiting_state_when_children_pending(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(parent.id, SpawnRequest(task="work"))

        waiting_states: list[str] = []
        call_count = 0

        async def run_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Schedule child completion after yielding control
                asyncio.get_event_loop().call_soon(
                    lambda: asyncio.ensure_future(
                        manager.complete_session(child.id, "child done")
                    )
                )
            waiting_states.append(parent.state)
            return _fake_result("done")

        mock = MagicMock()
        mock.run = run_side_effect

        with patch("nightowl.sessions.runner._build_agent", return_value=mock):
            await run_session(parent, manager, "start")

        assert SessionState.WAITING in waiting_states

    async def test_agent_rerun_after_child_completes(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(parent.id, SpawnRequest(task="work"))

        call_count = 0

        async def run_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                asyncio.get_event_loop().call_soon(
                    lambda: asyncio.ensure_future(
                        manager.complete_session(child.id, "child result")
                    )
                )
            return _fake_result(f"call {call_count}")

        mock = MagicMock()
        mock.run = run_side_effect

        with patch("nightowl.sessions.runner._build_agent", return_value=mock):
            response = await run_session(parent, manager, "start")

        # Initial run + one re-run after child completion
        assert call_count == 2
        assert response == "call 2"

    async def test_completion_message_passed_to_second_run(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(parent.id, SpawnRequest(task="fetch data"))

        messages_received: list[str] = []
        call_count = 0

        async def run_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if args:
                messages_received.append(args[0])
            if call_count == 1:
                asyncio.get_event_loop().call_soon(
                    lambda: asyncio.ensure_future(
                        manager.complete_session(child.id, "fetched data")
                    )
                )
            return _fake_result("done")

        mock = MagicMock()
        mock.run = run_side_effect

        with patch("nightowl.sessions.runner._build_agent", return_value=mock):
            await run_session(parent, manager, "start task")

        assert len(messages_received) == 2
        # Second message is the completion event from the child
        assert "fetched data" in messages_received[1]

    async def test_message_history_passed_on_rerun(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(parent.id, SpawnRequest(task="work"))

        fake_history = [{"role": "user", "content": "previous message"}]
        first_result = _fake_result("first response")
        first_result.new_messages = MagicMock(return_value=fake_history)
        second_result = _fake_result("second response")
        second_result.new_messages = MagicMock(return_value=[])

        results = [first_result, second_result]
        call_count = 0
        captured_kwargs: list[dict] = []

        async def run_side_effect(*args, **kwargs):
            nonlocal call_count
            captured_kwargs.append(kwargs)
            r = results[call_count]
            call_count += 1
            if call_count == 1:
                asyncio.get_event_loop().call_soon(
                    lambda: asyncio.ensure_future(
                        manager.complete_session(child.id, "done")
                    )
                )
            return r

        mock = MagicMock()
        mock.run = run_side_effect

        with patch("nightowl.sessions.runner._build_agent", return_value=mock):
            await run_session(parent, manager, "start")

        # Second call must have received message_history from first result
        assert len(captured_kwargs) == 2
        assert captured_kwargs[1].get("message_history") == fake_history

    async def test_loop_exits_when_all_completions_received(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        c1 = await manager.spawn_child(parent.id, SpawnRequest(task="a"))
        c2 = await manager.spawn_child(parent.id, SpawnRequest(task="b"))

        call_count = 0

        async def run_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                asyncio.get_event_loop().call_soon(
                    lambda: asyncio.ensure_future(
                        manager.complete_session(c1.id, "done a")
                    )
                )
            elif call_count == 2:
                asyncio.get_event_loop().call_soon(
                    lambda: asyncio.ensure_future(
                        manager.complete_session(c2.id, "done b")
                    )
                )
            return _fake_result(f"call {call_count}")

        mock = MagicMock()
        mock.run = run_side_effect

        with patch("nightowl.sessions.runner._build_agent", return_value=mock):
            response = await run_session(parent, manager, "start")

        # Initial + one per child completion
        assert call_count == 3
        assert response == "call 3"
        assert parent.state == SessionState.COMPLETED


class TestTimeoutHandling:
    async def test_timeout_exits_loop_without_raising(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        await manager.spawn_child(parent.id, SpawnRequest(task="never finishes"))

        mock = _mock_agent("partial answer")

        with patch("nightowl.sessions.runner._build_agent", return_value=mock):
            with patch(
                "nightowl.sessions.runner.asyncio.wait_for",
                side_effect=asyncio.TimeoutError,
            ):
                response = await run_session(parent, manager, "start")

        # Despite timeout, session completes with whatever the last response was
        assert parent.state == SessionState.COMPLETED
        assert response == "partial answer"

    async def test_timeout_session_result_is_set(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        await manager.spawn_child(parent.id, SpawnRequest(task="slow task"))

        with patch("nightowl.sessions.runner._build_agent", return_value=_mock_agent("timeout response")):
            with patch(
                "nightowl.sessions.runner.asyncio.wait_for",
                side_effect=asyncio.TimeoutError,
            ):
                await run_session(parent, manager, "start")

        assert parent.result == "timeout response"

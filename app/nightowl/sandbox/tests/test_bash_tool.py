"""Tests for the bash_exec Pydantic AI tool.

Module under test: nightowl/sandbox/bash_tool.py

bash_exec(ctx, command) runs a shell command inside the session's sandbox
container via DockerSandboxManager.exec_command(). Returns stdout/stderr.
Handles timeouts. Decorated with @hitl_gated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nightowl.sessions.manager import SessionManager
from nightowl.sessions.tools import AgentState
from nightowl.sandbox.bash_tool import bash_exec


@dataclass
class _FakeCtx:
    deps: AgentState


# ---------------------------------------------------------------------------
# Successful execution
# ---------------------------------------------------------------------------


class TestBashExecSuccess:
    async def test_returns_stdout_from_container(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value="container:abc")
        exec_result = MagicMock(stdout="file1.txt\nfile2.txt\n", stderr="", exit_code=0)
        sandbox_mgr.exec_command = AsyncMock(return_value=exec_result)

        state = AgentState(session_id=session.id, manager=manager)
        state.sandbox_manager = sandbox_mgr
        ctx = _FakeCtx(deps=state)

        with patch("nightowl.sandbox.bash_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            result = await bash_exec(ctx, command="ls", risk_level="low", risk_justification="list files")

        assert "file1.txt" in result

    async def test_passes_command_to_container(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value="container:abc")
        exec_result = MagicMock(stdout="", stderr="", exit_code=0)
        sandbox_mgr.exec_command = AsyncMock(return_value=exec_result)

        state = AgentState(session_id=session.id, manager=manager)
        state.sandbox_manager = sandbox_mgr
        ctx = _FakeCtx(deps=state)

        with patch("nightowl.sandbox.bash_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            await bash_exec(ctx, command="cat /etc/hostname", risk_level="low", risk_justification="check host")

        sandbox_mgr.exec_command.assert_called_once()
        call_str = str(sandbox_mgr.exec_command.call_args)
        assert "cat /etc/hostname" in call_str


# ---------------------------------------------------------------------------
# Error / failure cases
# ---------------------------------------------------------------------------


class TestBashExecErrors:
    async def test_returns_stderr_on_nonzero_exit(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value="container:abc")
        exec_result = MagicMock(stdout="", stderr="No such file or directory", exit_code=1)
        sandbox_mgr.exec_command = AsyncMock(return_value=exec_result)

        state = AgentState(session_id=session.id, manager=manager)
        state.sandbox_manager = sandbox_mgr
        ctx = _FakeCtx(deps=state)

        with patch("nightowl.sandbox.bash_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            result = await bash_exec(ctx, command="cat /nope", risk_level="low", risk_justification="test")

        assert "no such file" in result.lower() or "exit" in result.lower()

    async def test_no_container_returns_error(self, manager: SessionManager):
        """If no sandbox container exists for this session, return an error."""
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value=None)

        state = AgentState(session_id=session.id, manager=manager)
        state.sandbox_manager = sandbox_mgr
        ctx = _FakeCtx(deps=state)

        with patch("nightowl.sandbox.bash_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            result = await bash_exec(ctx, command="ls", risk_level="low", risk_justification="test")

        assert "error" in result.lower() or "no" in result.lower() and "container" in result.lower()

    async def test_no_sandbox_manager_returns_error(self, manager: SessionManager):
        """If no sandbox manager is configured at all."""
        session = await manager.create_main_session("test")
        state = AgentState(session_id=session.id, manager=manager)
        # No sandbox_manager attribute set
        ctx = _FakeCtx(deps=state)

        with patch("nightowl.sandbox.bash_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            result = await bash_exec(ctx, command="ls", risk_level="low", risk_justification="test")

        assert "error" in result.lower() or "sandbox" in result.lower()


# ---------------------------------------------------------------------------
# Output format
# ---------------------------------------------------------------------------


class TestBashExecOutput:
    async def test_includes_exit_code_on_failure(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value="container:abc")
        exec_result = MagicMock(stdout="", stderr="permission denied", exit_code=126)
        sandbox_mgr.exec_command = AsyncMock(return_value=exec_result)

        state = AgentState(session_id=session.id, manager=manager)
        state.sandbox_manager = sandbox_mgr
        ctx = _FakeCtx(deps=state)

        with patch("nightowl.sandbox.bash_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            result = await bash_exec(ctx, command="./noperm", risk_level="low", risk_justification="test")

        assert "126" in result or "permission" in result.lower()

    async def test_result_is_string(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value="container:abc")
        exec_result = MagicMock(stdout="ok", stderr="", exit_code=0)
        sandbox_mgr.exec_command = AsyncMock(return_value=exec_result)

        state = AgentState(session_id=session.id, manager=manager)
        state.sandbox_manager = sandbox_mgr
        ctx = _FakeCtx(deps=state)

        with patch("nightowl.sandbox.bash_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            result = await bash_exec(ctx, command="echo ok", risk_level="low", risk_justification="test")

        assert isinstance(result, str)

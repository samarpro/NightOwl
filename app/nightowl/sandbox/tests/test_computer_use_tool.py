"""Tests for computer use tools.

Module under test: nightowl/sandbox/computer_use_tool.py

computer_use_screenshot(ctx) — capture desktop via VNC/screenshot
computer_use_action(ctx, action, coords?, text?) — mouse/keyboard events

Uses Claude computer use API patterns. Runs inside the computer_use container
with Xvfb + VNC server.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nightowl.sessions.manager import SessionManager
from nightowl.sessions.tools import AgentState
from nightowl.sandbox.computer_use_tool import computer_use_screenshot, computer_use_action


@dataclass
class _FakeCtx:
    deps: AgentState


def _make_ctx_with_sandbox(session_id: str, manager: SessionManager, sandbox_mgr: MagicMock) -> _FakeCtx:
    state = AgentState(session_id=session_id, manager=manager)
    state.sandbox_manager = sandbox_mgr
    return _FakeCtx(deps=state)


# ---------------------------------------------------------------------------
# computer_use_screenshot
# ---------------------------------------------------------------------------


class TestComputerUseScreenshot:
    async def test_returns_screenshot_data(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value="container:cu1")
        sandbox_mgr.exec_command = AsyncMock(return_value=MagicMock(
            stdout="base64_screenshot_data_here", stderr="", exit_code=0,
        ))
        ctx = _make_ctx_with_sandbox(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.computer_use_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            result = await computer_use_screenshot(ctx, risk_level="low", risk_justification="check screen")

        assert result is not None
        assert len(str(result)) > 0

    async def test_no_container_returns_error(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value=None)
        ctx = _make_ctx_with_sandbox(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.computer_use_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            result = await computer_use_screenshot(ctx, risk_level="low", risk_justification="test")

        assert "error" in str(result).lower()


# ---------------------------------------------------------------------------
# computer_use_action
# ---------------------------------------------------------------------------


class TestComputerUseAction:
    async def test_click_action_with_coords(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value="container:cu1")
        sandbox_mgr.exec_command = AsyncMock(return_value=MagicMock(
            stdout='{"success": true}', stderr="", exit_code=0,
        ))
        ctx = _make_ctx_with_sandbox(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.computer_use_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "medium", "reasoning": "ok"}
            result = await computer_use_action(
                ctx, action="click", coords=[500, 300],
                risk_level="medium", risk_justification="click button",
            )

        call_str = str(sandbox_mgr.exec_command.call_args)
        assert "click" in call_str
        assert "500" in call_str and "300" in call_str

    async def test_type_action_with_text(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value="container:cu1")
        sandbox_mgr.exec_command = AsyncMock(return_value=MagicMock(
            stdout='{"success": true}', stderr="", exit_code=0,
        ))
        ctx = _make_ctx_with_sandbox(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.computer_use_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "medium", "reasoning": "ok"}
            result = await computer_use_action(
                ctx, action="type", text="hello world",
                risk_level="medium", risk_justification="type text",
            )

        call_str = str(sandbox_mgr.exec_command.call_args)
        assert "type" in call_str
        assert "hello world" in call_str

    async def test_scroll_action(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value="container:cu1")
        sandbox_mgr.exec_command = AsyncMock(return_value=MagicMock(
            stdout='{"success": true}', stderr="", exit_code=0,
        ))
        ctx = _make_ctx_with_sandbox(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.computer_use_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            result = await computer_use_action(
                ctx, action="scroll", coords=[500, 300],
                risk_level="low", risk_justification="scroll page",
            )

        call_str = str(sandbox_mgr.exec_command.call_args)
        assert "scroll" in call_str

    async def test_no_container_returns_error(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value=None)
        ctx = _make_ctx_with_sandbox(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.computer_use_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            result = await computer_use_action(
                ctx, action="click", coords=[0, 0],
                risk_level="low", risk_justification="test",
            )

        assert "error" in str(result).lower()

    async def test_result_is_string_or_dict(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value="container:cu1")
        sandbox_mgr.exec_command = AsyncMock(return_value=MagicMock(
            stdout='{"success": true}', stderr="", exit_code=0,
        ))
        ctx = _make_ctx_with_sandbox(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.computer_use_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            result = await computer_use_action(
                ctx, action="click", coords=[100, 200],
                risk_level="low", risk_justification="test",
            )

        assert isinstance(result, (str, dict))

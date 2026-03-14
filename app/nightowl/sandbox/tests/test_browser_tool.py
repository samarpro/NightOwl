"""Tests for browser tools.

Module under test: nightowl/sandbox/browser_tool.py

All tools auto-create a browser container via ensure_container() on first use.
Commands are serialised as JSON and executed via playwright-bridge inside the container.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nightowl.models.approval import RiskLevel
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.tools import AgentState
from nightowl.sandbox.browser_tool import browser_navigate, browser_interact, browser_screenshot


@dataclass
class _FakeCtx:
    deps: AgentState


def _mock_sandbox_mgr(stdout: str = "{}", stderr: str = "", exit_code: int = 0) -> MagicMock:
    mgr = MagicMock()
    mgr.ensure_container = AsyncMock(return_value="container:b1")
    mgr.exec_command = AsyncMock(return_value=MagicMock(
        stdout=stdout, stderr=stderr, exit_code=exit_code,
    ))
    return mgr


def _make_ctx(session_id: str, manager: SessionManager, sandbox_mgr: MagicMock) -> _FakeCtx:
    state = AgentState(session_id=session_id, manager=manager)
    state.sandbox_manager = sandbox_mgr
    return _FakeCtx(deps=state)


# ---------------------------------------------------------------------------
# browser_navigate
# ---------------------------------------------------------------------------


class TestBrowserNavigate:
    async def test_navigate_returns_page_content(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = _mock_sandbox_mgr(stdout='{"title": "Example", "text": "Hello"}')
        ctx = _make_ctx(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.browser_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            result = await browser_navigate(ctx, url="https://example.com", risk_level="low", risk_justification="read")

        assert isinstance(result, str)
        assert len(result) > 0

    async def test_navigate_forwards_url_to_container(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = _mock_sandbox_mgr()
        ctx = _make_ctx(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.browser_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            await browser_navigate(ctx, url="https://restaurant.com/menu", risk_level="low", risk_justification="read")

        call_str = str(sandbox_mgr.exec_command.call_args)
        assert "restaurant.com/menu" in call_str

    async def test_no_sandbox_manager_returns_error(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        state = AgentState(session_id=session.id, manager=manager)
        ctx = _FakeCtx(deps=state)

        with patch("nightowl.sandbox.browser_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            result = await browser_navigate(ctx, url="https://example.com", risk_level="low", risk_justification="read")

        assert "error" in str(result).lower()


# ---------------------------------------------------------------------------
# browser_interact
# ---------------------------------------------------------------------------


class TestBrowserInteract:
    async def test_click_action(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = _mock_sandbox_mgr(stdout='{"success": true}')
        ctx = _make_ctx(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.browser_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            await browser_interact(
                ctx, selector="#book-btn", action="click",
                risk_level="low", risk_justification="book reservation",
            )

        call_str = str(sandbox_mgr.exec_command.call_args)
        assert "#book-btn" in call_str
        assert "click" in call_str

    async def test_fill_action_passes_value(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = _mock_sandbox_mgr(stdout='{"success": true}')
        ctx = _make_ctx(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.browser_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            await browser_interact(
                ctx, selector="input[name=email]", action="fill", value="user@example.com",
                risk_level="low", risk_justification="fill form",
            )

        call_str = str(sandbox_mgr.exec_command.call_args)
        assert "user@example.com" in call_str

    async def test_no_sandbox_manager_returns_error(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        state = AgentState(session_id=session.id, manager=manager)
        ctx = _FakeCtx(deps=state)

        with patch("nightowl.sandbox.browser_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            result = await browser_interact(
                ctx, selector="#btn", action="click",
                risk_level="low", risk_justification="test",
            )

        assert "error" in str(result).lower()


# ---------------------------------------------------------------------------
# browser_screenshot
# ---------------------------------------------------------------------------


class TestBrowserScreenshot:
    async def test_returns_screenshot_data(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = _mock_sandbox_mgr(stdout="iVBORw0KGgo...")
        ctx = _make_ctx(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.browser_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            result = await browser_screenshot(ctx, risk_level="low", risk_justification="check page")

        assert isinstance(result, str)
        assert len(result) > 0

    async def test_no_sandbox_manager_returns_error(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        state = AgentState(session_id=session.id, manager=manager)
        ctx = _FakeCtx(deps=state)

        with patch("nightowl.sandbox.browser_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            result = await browser_screenshot(ctx, risk_level="low", risk_justification="test")

        assert "error" in str(result).lower()

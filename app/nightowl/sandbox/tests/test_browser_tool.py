"""Tests for browser tools.

Module under test: nightowl/sandbox/browser_tool.py

browser_navigate(ctx, url) — navigate to URL, return page snapshot
browser_interact(ctx, selector, action, value?) — click/fill/select on element
browser_screenshot(ctx) — return screenshot of current page

All route through Playwright running inside the browser sandbox container.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nightowl.sessions.manager import SessionManager
from nightowl.sessions.tools import AgentState
from nightowl.sandbox.browser_tool import browser_navigate, browser_interact, browser_screenshot


@dataclass
class _FakeCtx:
    deps: AgentState


def _make_ctx_with_sandbox(session_id: str, manager: SessionManager, sandbox_mgr: MagicMock) -> _FakeCtx:
    state = AgentState(session_id=session_id, manager=manager)
    state.sandbox_manager = sandbox_mgr
    return _FakeCtx(deps=state)


# ---------------------------------------------------------------------------
# browser_navigate
# ---------------------------------------------------------------------------


class TestBrowserNavigate:
    async def test_navigate_returns_page_content(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value="container:b1")
        sandbox_mgr.exec_command = AsyncMock(return_value=MagicMock(
            stdout='{"title": "Example", "text": "Hello World"}', stderr="", exit_code=0,
        ))
        ctx = _make_ctx_with_sandbox(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.browser_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            result = await browser_navigate(ctx, url="https://example.com", risk_level="low", risk_justification="read")

        assert isinstance(result, (str, dict))
        # Should contain something from the page
        result_str = str(result)
        assert len(result_str) > 0

    async def test_navigate_forwards_url_to_container(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value="container:b1")
        sandbox_mgr.exec_command = AsyncMock(return_value=MagicMock(
            stdout="{}", stderr="", exit_code=0,
        ))
        ctx = _make_ctx_with_sandbox(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.browser_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            await browser_navigate(ctx, url="https://restaurant.com/menu", risk_level="low", risk_justification="read")

        call_str = str(sandbox_mgr.exec_command.call_args)
        assert "restaurant.com/menu" in call_str

    async def test_no_container_returns_error(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value=None)
        ctx = _make_ctx_with_sandbox(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.browser_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            result = await browser_navigate(ctx, url="https://example.com", risk_level="low", risk_justification="read")

        assert "error" in str(result).lower() or "container" in str(result).lower()


# ---------------------------------------------------------------------------
# browser_interact
# ---------------------------------------------------------------------------


class TestBrowserInteract:
    async def test_click_action(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value="container:b1")
        sandbox_mgr.exec_command = AsyncMock(return_value=MagicMock(
            stdout='{"action": "click", "success": true}', stderr="", exit_code=0,
        ))
        ctx = _make_ctx_with_sandbox(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.browser_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            result = await browser_interact(
                ctx, selector="#book-btn", action="click",
                risk_level="medium", risk_justification="book reservation",
            )

        call_str = str(sandbox_mgr.exec_command.call_args)
        assert "#book-btn" in call_str
        assert "click" in call_str

    async def test_fill_action_passes_value(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value="container:b1")
        sandbox_mgr.exec_command = AsyncMock(return_value=MagicMock(
            stdout='{"success": true}', stderr="", exit_code=0,
        ))
        ctx = _make_ctx_with_sandbox(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.browser_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            await browser_interact(
                ctx, selector="input[name=email]", action="fill", value="user@example.com",
                risk_level="low", risk_justification="fill form",
            )

        call_str = str(sandbox_mgr.exec_command.call_args)
        assert "user@example.com" in call_str

    async def test_interact_without_container_returns_error(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value=None)
        ctx = _make_ctx_with_sandbox(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.browser_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
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
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value="container:b1")
        # Screenshot returns base64 or binary data
        sandbox_mgr.exec_command = AsyncMock(return_value=MagicMock(
            stdout="iVBORw0KGgo...", stderr="", exit_code=0,
        ))
        ctx = _make_ctx_with_sandbox(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.browser_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            result = await browser_screenshot(ctx, risk_level="low", risk_justification="check page")

        assert isinstance(result, (str, bytes, dict))
        assert len(str(result)) > 0

    async def test_screenshot_without_container_returns_error(self, manager: SessionManager):
        session = await manager.create_main_session("test")
        sandbox_mgr = MagicMock()
        sandbox_mgr.get_container_for_session = MagicMock(return_value=None)
        ctx = _make_ctx_with_sandbox(session.id, manager, sandbox_mgr)

        with patch("nightowl.sandbox.browser_tool.verify_risk", new_callable=AsyncMock) as mock_v:
            mock_v.return_value = {"verified_risk": "low", "reasoning": "ok"}
            result = await browser_screenshot(ctx, risk_level="low", risk_justification="test")

        assert "error" in str(result).lower()

"""Tests for Composio meta-tools — composio_search_tools and composio_execute.

Tests are written before the implementation (TDD). The module under test will
be nightowl/composio_tools/meta_tools.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nightowl.models.approval import RiskLevel
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.tools import AgentState
from nightowl.composio_tools.meta_tools import composio_search_tools, composio_execute


@dataclass
class _FakeCtx:
    deps: AgentState


def _make_ctx(session_id: str, manager: SessionManager) -> _FakeCtx:
    return _FakeCtx(deps=AgentState(session_id=session_id, manager=manager))


# ---------------------------------------------------------------------------
# composio_search_tools
# ---------------------------------------------------------------------------


class TestComposioSearchTools:
    async def test_returns_list_of_matching_tools(self, manager: SessionManager):
        parent = await manager.create_main_session("find calendar tools")
        ctx = _make_ctx(parent.id, manager)

        with patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client:
            mock_client.return_value.search_tools = AsyncMock(return_value=[
                {"name": "GOOGLECALENDAR_LIST_EVENTS", "description": "List events"},
                {"name": "GOOGLECALENDAR_CREATE_EVENT", "description": "Create event"},
            ])
            result = await composio_search_tools(ctx, query="google calendar")

        assert isinstance(result, list)
        assert len(result) == 2

    async def test_each_result_has_name_and_description(self, manager: SessionManager):
        parent = await manager.create_main_session("search tools")
        ctx = _make_ctx(parent.id, manager)

        with patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client:
            mock_client.return_value.search_tools = AsyncMock(return_value=[
                {"name": "GMAIL_SEND", "description": "Send an email via Gmail"},
            ])
            result = await composio_search_tools(ctx, query="gmail")

        assert "name" in result[0]
        assert "description" in result[0]

    async def test_empty_query_returns_empty_list(self, manager: SessionManager):
        parent = await manager.create_main_session("empty search")
        ctx = _make_ctx(parent.id, manager)

        with patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client:
            mock_client.return_value.search_tools = AsyncMock(return_value=[])
            result = await composio_search_tools(ctx, query="")

        assert result == []

    async def test_no_matches_returns_empty_list(self, manager: SessionManager):
        parent = await manager.create_main_session("no match search")
        ctx = _make_ctx(parent.id, manager)

        with patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client:
            mock_client.return_value.search_tools = AsyncMock(return_value=[])
            result = await composio_search_tools(ctx, query="nonexistent_integration_xyz")

        assert result == []

    async def test_composio_error_returns_error_string(self, manager: SessionManager):
        parent = await manager.create_main_session("error search")
        ctx = _make_ctx(parent.id, manager)

        with patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client:
            mock_client.return_value.search_tools = AsyncMock(
                side_effect=Exception("Composio API unavailable")
            )
            result = await composio_search_tools(ctx, query="calendar")

        # Should return a user-friendly error, not raise
        assert isinstance(result, str)
        assert "error" in result.lower()


# ---------------------------------------------------------------------------
# composio_execute
# ---------------------------------------------------------------------------


class TestComposioExecuteLowRisk:
    """Low-risk executions should go straight through with no HITL gate."""

    async def test_low_risk_executes_immediately(self, manager: SessionManager):
        parent = await manager.create_main_session("low risk exec")
        ctx = _make_ctx(parent.id, manager)

        with patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client:
            mock_client.return_value.execute_tool = AsyncMock(
                return_value={"status": "ok", "data": {"events": []}}
            )
            result = await composio_execute(
                ctx,
                tool_name="GOOGLECALENDAR_LIST_EVENTS",
                params={"calendar_id": "primary"},
                risk_level="low",
                risk_justification="Read-only calendar access",
            )

        assert isinstance(result, dict)
        assert result["status"] == "ok"

    async def test_low_risk_does_not_trigger_hitl(self, manager: SessionManager):
        parent = await manager.create_main_session("no hitl for low")
        ctx = _make_ctx(parent.id, manager)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.composio_tools.meta_tools._request_approval") as mock_approval,
        ):
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            await composio_execute(
                ctx,
                tool_name="GOOGLECALENDAR_LIST_EVENTS",
                params={},
                risk_level="low",
                risk_justification="Read-only",
            )

        mock_approval.assert_not_called()


class TestComposioExecuteRiskClassification:
    """Medium+ risk must go through the Haiku classifier before deciding on HITL."""

    async def test_medium_risk_triggers_classifier(self, manager: SessionManager):
        parent = await manager.create_main_session("medium risk")
        ctx = _make_ctx(parent.id, manager)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.composio_tools.meta_tools.verify_risk") as mock_verify,
            patch("nightowl.composio_tools.meta_tools._request_approval", new_callable=AsyncMock) as mock_approval,
        ):
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            mock_verify.return_value = {"verified_risk": RiskLevel.MEDIUM, "reasoning": "Correct assessment"}
            mock_approval.return_value = True
            await composio_execute(
                ctx,
                tool_name="GOOGLECALENDAR_CREATE_EVENT",
                params={"title": "Dinner"},
                risk_level="medium",
                risk_justification="Creating a calendar event",
            )

        mock_verify.assert_called_once()

    async def test_high_risk_triggers_classifier(self, manager: SessionManager):
        parent = await manager.create_main_session("high risk")
        ctx = _make_ctx(parent.id, manager)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.composio_tools.meta_tools.verify_risk") as mock_verify,
            patch("nightowl.composio_tools.meta_tools._request_approval", new_callable=AsyncMock) as mock_approval,
        ):
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            mock_verify.return_value = {"verified_risk": RiskLevel.HIGH, "reasoning": "Sends external message"}
            mock_approval.return_value = True
            await composio_execute(
                ctx,
                tool_name="GMAIL_SEND",
                params={"to": "alice@example.com", "body": "hello"},
                risk_level="high",
                risk_justification="Sending email to external party",
            )

        mock_verify.assert_called_once()

    async def test_classifier_downgrade_skips_hitl(self, manager: SessionManager):
        """If the agent says medium but Haiku says low, no HITL gate needed."""
        parent = await manager.create_main_session("downgraded risk")
        ctx = _make_ctx(parent.id, manager)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.composio_tools.meta_tools.verify_risk") as mock_verify,
            patch("nightowl.composio_tools.meta_tools._request_approval") as mock_approval,
        ):
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            # Agent says medium, Haiku says actually low
            mock_verify.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "False positive — read-only"}
            await composio_execute(
                ctx,
                tool_name="GOOGLECALENDAR_LIST_EVENTS",
                params={},
                risk_level="medium",
                risk_justification="Calendar access",
            )

        mock_approval.assert_not_called()

    async def test_classifier_upgrade_triggers_hitl(self, manager: SessionManager):
        """If the agent says medium but Haiku says high, HITL gate must fire."""
        parent = await manager.create_main_session("upgraded risk")
        ctx = _make_ctx(parent.id, manager)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.composio_tools.meta_tools.verify_risk") as mock_verify,
            patch("nightowl.composio_tools.meta_tools._request_approval", new_callable=AsyncMock) as mock_approval,
        ):
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            mock_verify.return_value = {"verified_risk": RiskLevel.HIGH, "reasoning": "Actually sends money"}
            mock_approval.return_value = True
            await composio_execute(
                ctx,
                tool_name="BANK_TRANSFER",
                params={"amount": 50},
                risk_level="medium",
                risk_justification="Small transfer",
            )

        mock_approval.assert_called_once()


class TestComposioExecuteHITLGating:
    """High/critical verified risk must block on HITL approval."""

    async def test_high_risk_approved_executes(self, manager: SessionManager):
        parent = await manager.create_main_session("approved exec")
        ctx = _make_ctx(parent.id, manager)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.composio_tools.meta_tools.verify_risk") as mock_verify,
            patch("nightowl.composio_tools.meta_tools._request_approval", new_callable=AsyncMock) as mock_approval,
        ):
            mock_client.return_value.execute_tool = AsyncMock(
                return_value={"status": "ok", "data": {"sent": True}}
            )
            mock_verify.return_value = {"verified_risk": RiskLevel.HIGH, "reasoning": "Sends email"}
            mock_approval.return_value = True

            result = await composio_execute(
                ctx,
                tool_name="GMAIL_SEND",
                params={"to": "bob@example.com"},
                risk_level="high",
                risk_justification="Sending email",
            )

        assert result["status"] == "ok"

    async def test_high_risk_rejected_does_not_execute(self, manager: SessionManager):
        parent = await manager.create_main_session("rejected exec")
        ctx = _make_ctx(parent.id, manager)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.composio_tools.meta_tools.verify_risk") as mock_verify,
            patch("nightowl.composio_tools.meta_tools._request_approval", new_callable=AsyncMock) as mock_approval,
        ):
            mock_verify.return_value = {"verified_risk": RiskLevel.HIGH, "reasoning": "Sends email"}
            mock_approval.return_value = False

            result = await composio_execute(
                ctx,
                tool_name="GMAIL_SEND",
                params={"to": "bob@example.com"},
                risk_level="high",
                risk_justification="Sending email",
            )

        # Tool must NOT have been called
        mock_client.return_value.execute_tool.assert_not_called()
        # Result should indicate rejection
        assert isinstance(result, str)
        assert "denied" in result.lower() or "rejected" in result.lower()

    async def test_critical_risk_approved_executes(self, manager: SessionManager):
        parent = await manager.create_main_session("critical approved")
        ctx = _make_ctx(parent.id, manager)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.composio_tools.meta_tools.verify_risk") as mock_verify,
            patch("nightowl.composio_tools.meta_tools._request_approval", new_callable=AsyncMock) as mock_approval,
        ):
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            mock_verify.return_value = {"verified_risk": RiskLevel.CRITICAL, "reasoning": "Payment"}
            mock_approval.return_value = True

            result = await composio_execute(
                ctx,
                tool_name="STRIPE_CHARGE",
                params={"amount": 9999},
                risk_level="critical",
                risk_justification="Processing payment",
            )

        assert result["status"] == "ok"


class TestComposioExecuteParams:
    """Argument validation and passthrough."""

    async def test_params_passed_through_to_composio(self, manager: SessionManager):
        parent = await manager.create_main_session("param passthrough")
        ctx = _make_ctx(parent.id, manager)
        expected_params = {"calendar_id": "primary", "max_results": 10}

        with patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client:
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            await composio_execute(
                ctx,
                tool_name="GOOGLECALENDAR_LIST_EVENTS",
                params=expected_params,
                risk_level="low",
                risk_justification="Read-only",
            )

        mock_client.return_value.execute_tool.assert_called_once()
        call_args = mock_client.return_value.execute_tool.call_args
        assert call_args[1].get("params") == expected_params or call_args[0][1] == expected_params

    async def test_empty_params_accepted(self, manager: SessionManager):
        parent = await manager.create_main_session("empty params")
        ctx = _make_ctx(parent.id, manager)

        with patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client:
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            result = await composio_execute(
                ctx,
                tool_name="GOOGLECALENDAR_LIST_EVENTS",
                params={},
                risk_level="low",
                risk_justification="Read-only",
            )

        assert result["status"] == "ok"

    async def test_composio_execution_error_returns_error(self, manager: SessionManager):
        parent = await manager.create_main_session("exec error")
        ctx = _make_ctx(parent.id, manager)

        with patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client:
            mock_client.return_value.execute_tool = AsyncMock(
                side_effect=Exception("Tool execution failed")
            )
            result = await composio_execute(
                ctx,
                tool_name="BROKEN_TOOL",
                params={},
                risk_level="low",
                risk_justification="Testing",
            )

        assert isinstance(result, str)
        assert "error" in result.lower()

    async def test_risk_level_string_parsed_to_enum(self, manager: SessionManager):
        """risk_level arg is a string from the LLM — must parse to RiskLevel."""
        parent = await manager.create_main_session("risk parsing")
        ctx = _make_ctx(parent.id, manager)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.composio_tools.meta_tools.verify_risk") as mock_verify,
            patch("nightowl.composio_tools.meta_tools._request_approval", new_callable=AsyncMock) as mock_approval,
        ):
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            mock_verify.return_value = {"verified_risk": RiskLevel.HIGH, "reasoning": "ok"}
            mock_approval.return_value = True

            # Passing string "high" — should not crash
            await composio_execute(
                ctx,
                tool_name="SOME_TOOL",
                params={},
                risk_level="high",
                risk_justification="Reason",
            )

        # verify_risk should have received a RiskLevel enum, not a raw string
        call_kwargs = mock_verify.call_args
        self_reported = call_kwargs[1].get("self_reported_risk") or call_kwargs[0][2]
        assert isinstance(self_reported, RiskLevel)

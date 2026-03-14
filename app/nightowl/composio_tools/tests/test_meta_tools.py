"""Tests for Composio meta-tools — composio_search_tools and composio_execute.

The HITL logic lives in the @hitl_gated decorator (nightowl.hitl.decorator).
Classifier runs on LOW/MEDIUM. HIGH/CRITICAL go straight to HITL.
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


def _make_ctx(session_id: str, manager: SessionManager, gate: Any = None) -> _FakeCtx:
    return _FakeCtx(deps=AgentState(session_id=session_id, manager=manager, hitl_gate=gate))


# ---------------------------------------------------------------------------
# composio_search_tools
# ---------------------------------------------------------------------------


class TestComposioSearchTools:
    async def test_forwards_query_to_composio_client(self, manager: SessionManager):
        parent = await manager.create_main_session("find calendar tools")
        ctx = _make_ctx(parent.id, manager)

        with patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client:
            mock_client.return_value.search_tools = AsyncMock(return_value=[])
            await composio_search_tools(ctx, query="google calendar events")

        mock_client.return_value.search_tools.assert_called_once()
        call_str = str(mock_client.return_value.search_tools.call_args)
        assert "google calendar events" in call_str

    async def test_composio_error_returns_error_string_not_exception(self, manager: SessionManager):
        parent = await manager.create_main_session("error search")
        ctx = _make_ctx(parent.id, manager)

        with patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client:
            mock_client.return_value.search_tools = AsyncMock(
                side_effect=Exception("Composio API unavailable")
            )
            result = await composio_search_tools(ctx, query="calendar")

        assert isinstance(result, str)
        assert "error" in result.lower()

    async def test_result_is_always_list_or_error_string(self, manager: SessionManager):
        parent = await manager.create_main_session("type check")
        ctx = _make_ctx(parent.id, manager)

        with patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client:
            mock_client.return_value.search_tools = AsyncMock(return_value=[
                {"name": "TOOL_A", "description": "Does A"},
            ])
            result = await composio_search_tools(ctx, query="anything")

        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)


# ---------------------------------------------------------------------------
# composio_execute — LOW risk: runs classifier to catch underreported danger
# ---------------------------------------------------------------------------


class TestComposioExecuteLowRisk:
    async def test_low_risk_runs_classifier(self, manager: SessionManager):
        """LOW risk goes through classifier — catches underreported danger."""
        parent = await manager.create_main_session("classifier for low")
        ctx = _make_ctx(parent.id, manager)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.hitl.decorator.verify_risk") as mock_verify,
        ):
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            mock_verify.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "Confirmed low"}
            await composio_execute(
                ctx,
                tool_name="GOOGLECALENDAR_LIST_EVENTS",
                params={},
                risk_level="low",
                risk_justification="Read-only",
            )

        mock_verify.assert_called_once()

    async def test_low_confirmed_skips_hitl(self, manager: SessionManager):
        """Classifier confirms LOW → no HITL, tool executes."""
        mock_gate = MagicMock()
        mock_gate.request_approval = AsyncMock()
        parent = await manager.create_main_session("low confirmed")
        ctx = _make_ctx(parent.id, manager, gate=mock_gate)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.hitl.decorator.verify_risk") as mock_verify,
        ):
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            mock_verify.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "Confirmed low"}
            await composio_execute(
                ctx,
                tool_name="GOOGLECALENDAR_LIST_EVENTS",
                params={},
                risk_level="low",
                risk_justification="Read-only",
            )

        mock_gate.request_approval.assert_not_called()
        mock_client.return_value.execute_tool.assert_called_once()

    async def test_low_upgraded_to_high_triggers_hitl(self, manager: SessionManager):
        """Agent says low, classifier says high → HITL fires."""
        mock_gate = MagicMock()
        mock_gate.request_approval = AsyncMock(return_value=True)
        parent = await manager.create_main_session("low upgraded")
        ctx = _make_ctx(parent.id, manager, gate=mock_gate)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.hitl.decorator.verify_risk") as mock_verify,
        ):
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            mock_verify.return_value = {"verified_risk": RiskLevel.HIGH, "reasoning": "This drops a table"}
            await composio_execute(
                ctx,
                tool_name="DATABASE_QUERY",
                params={"sql": "DROP TABLE users"},
                risk_level="low",
                risk_justification="Just a query",
            )

        mock_gate.request_approval.assert_called_once()


# ---------------------------------------------------------------------------
# composio_execute — MEDIUM risk: runs classifier
# ---------------------------------------------------------------------------


class TestComposioExecuteMediumRisk:
    async def test_medium_risk_triggers_classifier(self, manager: SessionManager):
        mock_gate = MagicMock()
        mock_gate.request_approval = AsyncMock(return_value=True)
        parent = await manager.create_main_session("medium risk")
        ctx = _make_ctx(parent.id, manager, gate=mock_gate)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.hitl.decorator.verify_risk") as mock_verify,
        ):
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            mock_verify.return_value = {"verified_risk": RiskLevel.MEDIUM, "reasoning": "Correct"}
            await composio_execute(
                ctx,
                tool_name="GOOGLECALENDAR_CREATE_EVENT",
                params={"title": "Dinner"},
                risk_level="medium",
                risk_justification="Creating a calendar event",
            )

        mock_verify.assert_called_once()

    async def test_classifier_downgrade_skips_hitl(self, manager: SessionManager):
        """Agent says medium, classifier says low → no HITL."""
        mock_gate = MagicMock()
        mock_gate.request_approval = AsyncMock()
        parent = await manager.create_main_session("downgraded risk")
        ctx = _make_ctx(parent.id, manager, gate=mock_gate)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.hitl.decorator.verify_risk") as mock_verify,
        ):
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            mock_verify.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "False positive"}
            await composio_execute(
                ctx,
                tool_name="GOOGLECALENDAR_LIST_EVENTS",
                params={},
                risk_level="medium",
                risk_justification="Calendar access",
            )

        mock_gate.request_approval.assert_not_called()
        mock_client.return_value.execute_tool.assert_called_once()

    async def test_classifier_upgrade_triggers_hitl(self, manager: SessionManager):
        """Agent says medium, classifier says high → HITL fires."""
        mock_gate = MagicMock()
        mock_gate.request_approval = AsyncMock(return_value=True)
        parent = await manager.create_main_session("upgraded risk")
        ctx = _make_ctx(parent.id, manager, gate=mock_gate)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.hitl.decorator.verify_risk") as mock_verify,
        ):
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            mock_verify.return_value = {"verified_risk": RiskLevel.HIGH, "reasoning": "Actually sends money"}
            await composio_execute(
                ctx,
                tool_name="BANK_TRANSFER",
                params={"amount": 50},
                risk_level="medium",
                risk_justification="Small transfer",
            )

        mock_gate.request_approval.assert_called_once()


# ---------------------------------------------------------------------------
# composio_execute — HIGH/CRITICAL: skip classifier, straight to HITL
# ---------------------------------------------------------------------------


class TestComposioExecuteHighRisk:
    async def test_high_risk_skips_classifier(self, manager: SessionManager):
        """HIGH goes straight to HITL — no need for classifier."""
        mock_gate = MagicMock()
        mock_gate.request_approval = AsyncMock(return_value=True)
        parent = await manager.create_main_session("high skip classifier")
        ctx = _make_ctx(parent.id, manager, gate=mock_gate)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.hitl.decorator.verify_risk") as mock_verify,
        ):
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            await composio_execute(
                ctx,
                tool_name="GMAIL_SEND",
                params={"to": "alice@example.com"},
                risk_level="high",
                risk_justification="Sending email",
            )

        mock_verify.assert_not_called()
        mock_gate.request_approval.assert_called_once()

    async def test_high_approved_executes_tool(self, manager: SessionManager):
        mock_gate = MagicMock()
        mock_gate.request_approval = AsyncMock(return_value=True)
        parent = await manager.create_main_session("approved exec")
        ctx = _make_ctx(parent.id, manager, gate=mock_gate)

        with patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client:
            mock_client.return_value.execute_tool = AsyncMock(
                return_value={"status": "ok", "data": {"sent": True}}
            )
            await composio_execute(
                ctx,
                tool_name="GMAIL_SEND",
                params={"to": "bob@example.com"},
                risk_level="high",
                risk_justification="Sending email",
            )

        mock_client.return_value.execute_tool.assert_called_once()

    async def test_high_rejected_never_executes_tool(self, manager: SessionManager):
        mock_gate = MagicMock()
        mock_gate.request_approval = AsyncMock(return_value=False)
        parent = await manager.create_main_session("rejected exec")
        ctx = _make_ctx(parent.id, manager, gate=mock_gate)

        with patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client:
            mock_client.return_value.execute_tool = AsyncMock()
            result = await composio_execute(
                ctx,
                tool_name="GMAIL_SEND",
                params={"to": "bob@example.com"},
                risk_level="high",
                risk_justification="Sending email",
            )

        mock_client.return_value.execute_tool.assert_not_called()
        assert isinstance(result, str)
        assert "denied" in result.lower() or "rejected" in result.lower()

    async def test_critical_skips_classifier_and_gates(self, manager: SessionManager):
        mock_gate = MagicMock()
        mock_gate.request_approval = AsyncMock(return_value=True)
        parent = await manager.create_main_session("critical gating")
        ctx = _make_ctx(parent.id, manager, gate=mock_gate)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.hitl.decorator.verify_risk") as mock_verify,
        ):
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            await composio_execute(
                ctx,
                tool_name="STRIPE_CHARGE",
                params={"amount": 9999},
                risk_level="critical",
                risk_justification="Processing payment",
            )

        mock_verify.assert_not_called()
        mock_gate.request_approval.assert_called_once()
        mock_client.return_value.execute_tool.assert_called_once()


# ---------------------------------------------------------------------------
# composio_execute — argument validation and passthrough
# ---------------------------------------------------------------------------


class TestComposioExecuteParams:
    async def test_tool_name_forwarded_to_composio(self, manager: SessionManager):
        parent = await manager.create_main_session("tool name passthrough")
        ctx = _make_ctx(parent.id, manager)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.hitl.decorator.verify_risk") as mock_verify,
        ):
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            mock_verify.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            await composio_execute(
                ctx,
                tool_name="GOOGLECALENDAR_LIST_EVENTS",
                params={"calendar_id": "primary"},
                risk_level="low",
                risk_justification="Read-only",
            )

        call_str = str(mock_client.return_value.execute_tool.call_args)
        assert "GOOGLECALENDAR_LIST_EVENTS" in call_str

    async def test_params_forwarded_to_composio(self, manager: SessionManager):
        parent = await manager.create_main_session("param passthrough")
        ctx = _make_ctx(parent.id, manager)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.hitl.decorator.verify_risk") as mock_verify,
        ):
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            mock_verify.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            await composio_execute(
                ctx,
                tool_name="GOOGLECALENDAR_LIST_EVENTS",
                params={"calendar_id": "primary", "max_results": 10},
                risk_level="low",
                risk_justification="Read-only",
            )

        call_str = str(mock_client.return_value.execute_tool.call_args)
        assert "primary" in call_str
        assert "10" in call_str

    async def test_composio_execution_error_returns_error(self, manager: SessionManager):
        parent = await manager.create_main_session("exec error")
        ctx = _make_ctx(parent.id, manager)

        with (
            patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client,
            patch("nightowl.hitl.decorator.verify_risk") as mock_verify,
        ):
            mock_client.return_value.execute_tool = AsyncMock(
                side_effect=Exception("Tool execution failed")
            )
            mock_verify.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            result = await composio_execute(
                ctx,
                tool_name="BROKEN_TOOL",
                params={},
                risk_level="low",
                risk_justification="Testing",
            )

        assert isinstance(result, str)
        assert "error" in result.lower()

    async def test_uppercase_risk_level_handled(self, manager: SessionManager):
        """LLM might send 'HIGH' or 'Low' — must normalise."""
        mock_gate = MagicMock()
        mock_gate.request_approval = AsyncMock(return_value=True)
        parent = await manager.create_main_session("uppercase risk")
        ctx = _make_ctx(parent.id, manager, gate=mock_gate)

        with patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client:
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})
            await composio_execute(
                ctx,
                tool_name="TOOL",
                params={},
                risk_level="HIGH",
                risk_justification="Sending",
            )

        # HIGH skips classifier, goes to gate
        mock_gate.request_approval.assert_called_once()

    async def test_invalid_risk_level_string_does_not_silently_execute(self, manager: SessionManager):
        parent = await manager.create_main_session("bad risk")
        ctx = _make_ctx(parent.id, manager)

        with patch("nightowl.composio_tools.meta_tools._get_composio_client") as mock_client:
            mock_client.return_value.execute_tool = AsyncMock(return_value={"status": "ok"})

            result = await composio_execute(
                ctx,
                tool_name="TOOL",
                params={},
                risk_level="banana",
                risk_justification="bad",
            )

            assert isinstance(result, str)
            assert "error" in result.lower() or "invalid" in result.lower()
            mock_client.return_value.execute_tool.assert_not_called()

"""Tests for the Haiku risk verification classifier.

Module under test: nightowl/hitl/classifier.py
Function: verify_risk(tool_name, tool_args, self_reported_risk, justification, session_context)
Returns: {"verified_risk": RiskLevel, "reasoning": str}

The classifier calls Haiku via Bedrock to second-guess the agent's self-reported
risk level. It only runs when self_reported_risk >= MEDIUM.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from nightowl.models.approval import RiskLevel
from nightowl.hitl.classifier import verify_risk


# ---------------------------------------------------------------------------
# Fast-path: LOW risk skips the classifier entirely
# ---------------------------------------------------------------------------


class TestLowRiskBypass:
    async def test_low_risk_returns_low_without_calling_bedrock(self):
        with patch("nightowl.hitl.classifier._call_haiku") as mock_haiku:
            result = await verify_risk(
                tool_name="GOOGLECALENDAR_LIST_EVENTS",
                tool_args={"calendar_id": "primary"},
                self_reported_risk=RiskLevel.LOW,
                justification="Read-only calendar listing",
            )

        mock_haiku.assert_not_called()
        assert result["verified_risk"] == RiskLevel.LOW

    async def test_low_risk_returns_passthrough_reasoning(self):
        result = await verify_risk(
            tool_name="WEB_SEARCH",
            tool_args={"query": "best restaurants sydney"},
            self_reported_risk=RiskLevel.LOW,
            justification="Public web search",
        )
        assert "reasoning" in result
        assert isinstance(result["reasoning"], str)


# ---------------------------------------------------------------------------
# MEDIUM risk: classifier runs
# ---------------------------------------------------------------------------


class TestMediumRiskClassification:
    async def test_medium_risk_calls_haiku(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "medium", "reasoning": "Correct assessment"}
            await verify_risk(
                tool_name="GOOGLECALENDAR_CREATE_EVENT",
                tool_args={"title": "Team dinner", "date": "2026-03-20"},
                self_reported_risk=RiskLevel.MEDIUM,
                justification="Creating calendar event",
            )

        mock_haiku.assert_called_once()

    async def test_medium_confirmed_returns_medium(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "medium", "reasoning": "Creates event, non-destructive"}
            result = await verify_risk(
                tool_name="GOOGLECALENDAR_CREATE_EVENT",
                tool_args={"title": "Dinner"},
                self_reported_risk=RiskLevel.MEDIUM,
                justification="Creating event",
            )

        assert result["verified_risk"] == RiskLevel.MEDIUM

    async def test_medium_downgraded_to_low(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "low", "reasoning": "Read-only operation despite agent claim"}
            result = await verify_risk(
                tool_name="GOOGLECALENDAR_LIST_EVENTS",
                tool_args={},
                self_reported_risk=RiskLevel.MEDIUM,
                justification="Checking calendar",
            )

        assert result["verified_risk"] == RiskLevel.LOW

    async def test_medium_upgraded_to_high(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "high", "reasoning": "Sends to external recipient"}
            result = await verify_risk(
                tool_name="GMAIL_SEND",
                tool_args={"to": "external@company.com", "body": "contract details"},
                self_reported_risk=RiskLevel.MEDIUM,
                justification="Sending email",
            )

        assert result["verified_risk"] == RiskLevel.HIGH


# ---------------------------------------------------------------------------
# HIGH risk: classifier runs
# ---------------------------------------------------------------------------


class TestHighRiskClassification:
    async def test_high_risk_calls_haiku(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "high", "reasoning": "Correct"}
            await verify_risk(
                tool_name="GMAIL_SEND",
                tool_args={"to": "alice@example.com"},
                self_reported_risk=RiskLevel.HIGH,
                justification="Sending email",
            )

        mock_haiku.assert_called_once()

    async def test_high_confirmed_returns_high(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "high", "reasoning": "External communication"}
            result = await verify_risk(
                tool_name="GMAIL_SEND",
                tool_args={"to": "ceo@company.com"},
                self_reported_risk=RiskLevel.HIGH,
                justification="Sending email to CEO",
            )

        assert result["verified_risk"] == RiskLevel.HIGH

    async def test_high_downgraded_to_medium(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "medium", "reasoning": "Internal draft, not sending"}
            result = await verify_risk(
                tool_name="GMAIL_CREATE_DRAFT",
                tool_args={"body": "draft text"},
                self_reported_risk=RiskLevel.HIGH,
                justification="Drafting email",
            )

        assert result["verified_risk"] == RiskLevel.MEDIUM

    async def test_high_upgraded_to_critical(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "critical", "reasoning": "Financial transaction"}
            result = await verify_risk(
                tool_name="STRIPE_CHARGE",
                tool_args={"amount": 5000, "currency": "usd"},
                self_reported_risk=RiskLevel.HIGH,
                justification="Processing payment",
            )

        assert result["verified_risk"] == RiskLevel.CRITICAL


# ---------------------------------------------------------------------------
# CRITICAL risk: classifier runs
# ---------------------------------------------------------------------------


class TestCriticalRiskClassification:
    async def test_critical_confirmed(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "critical", "reasoning": "Deletes user data"}
            result = await verify_risk(
                tool_name="DATABASE_DELETE",
                tool_args={"table": "users", "where": "id=1"},
                self_reported_risk=RiskLevel.CRITICAL,
                justification="Deleting user account",
            )

        assert result["verified_risk"] == RiskLevel.CRITICAL

    async def test_critical_downgraded(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "high", "reasoning": "Soft delete, reversible"}
            result = await verify_risk(
                tool_name="USER_DEACTIVATE",
                tool_args={"user_id": "123"},
                self_reported_risk=RiskLevel.CRITICAL,
                justification="Deactivating user",
            )

        assert result["verified_risk"] == RiskLevel.HIGH


# ---------------------------------------------------------------------------
# Return shape and edge cases
# ---------------------------------------------------------------------------


class TestClassifierReturnShape:
    async def test_result_has_verified_risk_key(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "medium", "reasoning": "ok"}
            result = await verify_risk(
                tool_name="TOOL",
                tool_args={},
                self_reported_risk=RiskLevel.MEDIUM,
                justification="test",
            )

        assert "verified_risk" in result

    async def test_result_has_reasoning_key(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "medium", "reasoning": "Some reasoning"}
            result = await verify_risk(
                tool_name="TOOL",
                tool_args={},
                self_reported_risk=RiskLevel.MEDIUM,
                justification="test",
            )

        assert "reasoning" in result
        assert len(result["reasoning"]) > 0

    async def test_verified_risk_is_always_a_risk_level_enum(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "high", "reasoning": "ok"}
            result = await verify_risk(
                tool_name="TOOL",
                tool_args={},
                self_reported_risk=RiskLevel.HIGH,
                justification="test",
            )

        assert isinstance(result["verified_risk"], RiskLevel)

    async def test_session_context_forwarded_to_haiku(self):
        """When session_context is provided, it should be included in the Haiku prompt."""
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "medium", "reasoning": "ok"}
            await verify_risk(
                tool_name="TOOL",
                tool_args={},
                self_reported_risk=RiskLevel.MEDIUM,
                justification="test",
                session_context="User is planning a night out, currently searching restaurants",
            )

        call_args = mock_haiku.call_args
        # The session context should appear somewhere in the prompt sent to Haiku
        prompt_content = str(call_args)
        assert "planning a night out" in prompt_content

    async def test_haiku_error_falls_back_to_self_reported_risk(self):
        """If Haiku fails, trust the agent's self-report rather than blocking."""
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.side_effect = Exception("Bedrock timeout")
            result = await verify_risk(
                tool_name="GMAIL_SEND",
                tool_args={},
                self_reported_risk=RiskLevel.HIGH,
                justification="Sending email",
            )

        # Fallback: trust the agent's claim
        assert result["verified_risk"] == RiskLevel.HIGH
        assert "error" in result["reasoning"].lower() or "fallback" in result["reasoning"].lower()

    async def test_haiku_returns_invalid_risk_falls_back(self):
        """If Haiku returns gibberish, fall back to self-reported risk."""
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "banana", "reasoning": "confused"}
            result = await verify_risk(
                tool_name="TOOL",
                tool_args={},
                self_reported_risk=RiskLevel.MEDIUM,
                justification="test",
            )

        assert result["verified_risk"] == RiskLevel.MEDIUM

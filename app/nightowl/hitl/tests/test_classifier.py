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
from nightowl.hitl.classifier import verify_risk, _HAIKU_MODEL


# ---------------------------------------------------------------------------
# Model configuration: catches hallucinated model IDs before they hit prod
# ---------------------------------------------------------------------------


class TestModelConfiguration:
    def test_haiku_model_id_matches_bedrock_format(self):
        """The model ID must follow Bedrock's naming convention.

        This test exists because the original model ID was hallucinated
        ('au.anthropic.claude-haiku-4-5-v1'). If the ID is wrong, Bedrock
        rejects every call and the classifier silently falls back to
        self-reported risk — defeating its entire purpose.
        """
        # Bedrock model IDs follow: [region.]anthropic.claude-<variant>-<date>-v<n>:<rev>
        assert "anthropic.claude-" in _HAIKU_MODEL, (
            f"{_HAIKU_MODEL!r} doesn't match Bedrock model ID format"
        )
        # Must include a date stamp (YYYYMMDD) — IDs without one are fake
        import re
        assert re.search(r"\d{8}", _HAIKU_MODEL), (
            f"{_HAIKU_MODEL!r} is missing a date stamp — likely hallucinated"
        )

    def test_haiku_model_is_actually_haiku(self):
        """The classifier must use a Haiku model, not Opus/Sonnet — it needs to be fast and cheap."""
        assert "haiku" in _HAIKU_MODEL.lower(), (
            f"Classifier model {_HAIKU_MODEL!r} doesn't look like a Haiku model"
        )


# ---------------------------------------------------------------------------
# LOW risk: classifier still runs (catches underreported danger)
# ---------------------------------------------------------------------------


class TestLowRiskClassification:
    async def test_low_risk_calls_haiku(self):
        """LOW risk still runs through classifier — catches 'low' claims that are actually dangerous."""
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "low", "reasoning": "Confirmed low"}
            await verify_risk(
                tool_name="GOOGLECALENDAR_LIST_EVENTS",
                tool_args={"calendar_id": "primary"},
                self_reported_risk=RiskLevel.LOW,
                justification="Read-only calendar listing",
            )

        mock_haiku.assert_called_once()

    async def test_low_confirmed_returns_low(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "low", "reasoning": "Confirmed read-only"}
            result = await verify_risk(
                tool_name="WEB_SEARCH",
                tool_args={"query": "best restaurants sydney"},
                self_reported_risk=RiskLevel.LOW,
                justification="Public web search",
            )

        assert result["verified_risk"] == RiskLevel.LOW

    async def test_low_upgraded_to_high(self):
        """The whole point — agent says low but classifier catches the danger."""
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "high", "reasoning": "This deletes production data"}
            result = await verify_risk(
                tool_name="DATABASE_QUERY",
                tool_args={"sql": "DROP TABLE users"},
                self_reported_risk=RiskLevel.LOW,
                justification="Just a database query",
            )

        assert result["verified_risk"] == RiskLevel.HIGH


# ---------------------------------------------------------------------------
# Classifier invocation: MEDIUM, HIGH, CRITICAL all call Haiku
# ---------------------------------------------------------------------------


class TestClassifierInvocation:
    async def test_medium_risk_calls_haiku(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "medium", "reasoning": "Correct"}
            await verify_risk(
                tool_name="GOOGLECALENDAR_CREATE_EVENT",
                tool_args={"title": "Team dinner"},
                self_reported_risk=RiskLevel.MEDIUM,
                justification="Creating calendar event",
            )

        mock_haiku.assert_called_once()

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

    async def test_critical_risk_calls_haiku(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "critical", "reasoning": "Correct"}
            await verify_risk(
                tool_name="DATABASE_DELETE",
                tool_args={"table": "users"},
                self_reported_risk=RiskLevel.CRITICAL,
                justification="Deleting data",
            )

        mock_haiku.assert_called_once()


# ---------------------------------------------------------------------------
# Haiku receives the right context to make its decision
# ---------------------------------------------------------------------------


class TestClassifierInputs:
    async def test_tool_name_forwarded_to_haiku(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "high", "reasoning": "ok"}
            await verify_risk(
                tool_name="GMAIL_SEND",
                tool_args={"to": "alice@example.com"},
                self_reported_risk=RiskLevel.HIGH,
                justification="Sending email",
            )

        call_str = str(mock_haiku.call_args)
        assert "GMAIL_SEND" in call_str

    async def test_tool_args_forwarded_to_haiku(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "high", "reasoning": "ok"}
            await verify_risk(
                tool_name="GMAIL_SEND",
                tool_args={"to": "ceo@megacorp.com", "body": "contract attached"},
                self_reported_risk=RiskLevel.HIGH,
                justification="Sending email",
            )

        call_str = str(mock_haiku.call_args)
        assert "ceo@megacorp.com" in call_str

    async def test_justification_forwarded_to_haiku(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "medium", "reasoning": "ok"}
            await verify_risk(
                tool_name="TOOL",
                tool_args={},
                self_reported_risk=RiskLevel.MEDIUM,
                justification="Agent wants to create a draft for review",
            )

        call_str = str(mock_haiku.call_args)
        assert "create a draft for review" in call_str

    async def test_session_context_forwarded_to_haiku(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "medium", "reasoning": "ok"}
            await verify_risk(
                tool_name="TOOL",
                tool_args={},
                self_reported_risk=RiskLevel.MEDIUM,
                justification="test",
                session_context="User is planning a night out, currently searching restaurants",
            )

        call_str = str(mock_haiku.call_args)
        assert "planning a night out" in call_str

    async def test_self_reported_risk_forwarded_to_haiku(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "high", "reasoning": "ok"}
            await verify_risk(
                tool_name="TOOL",
                tool_args={},
                self_reported_risk=RiskLevel.HIGH,
                justification="test",
            )

        call_str = str(mock_haiku.call_args)
        assert "high" in call_str.lower()


# ---------------------------------------------------------------------------
# Return value: string-to-enum coercion
# ---------------------------------------------------------------------------


class TestReturnValueCoercion:
    """Haiku returns raw strings. verify_risk must coerce to RiskLevel."""

    async def test_verified_risk_is_always_a_risk_level_enum(self):
        for risk_str in ("low", "medium", "high", "critical"):
            with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
                mock_haiku.return_value = {"verified_risk": risk_str, "reasoning": "ok"}
                result = await verify_risk(
                    tool_name="TOOL",
                    tool_args={},
                    self_reported_risk=RiskLevel.MEDIUM,
                    justification="test",
                )

            assert isinstance(result["verified_risk"], RiskLevel), (
                f"Expected RiskLevel enum for '{risk_str}', got {type(result['verified_risk'])}"
            )

    async def test_reasoning_is_always_a_nonempty_string(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"verified_risk": "medium", "reasoning": "Looks correct"}
            result = await verify_risk(
                tool_name="TOOL",
                tool_args={},
                self_reported_risk=RiskLevel.MEDIUM,
                justification="test",
            )

        assert isinstance(result["reasoning"], str)
        assert len(result["reasoning"]) > 0


# ---------------------------------------------------------------------------
# Error handling and fallback behaviour
# ---------------------------------------------------------------------------


class TestClassifierFallback:
    async def test_haiku_timeout_falls_back_to_self_reported(self):
        """If Haiku fails, trust the agent's self-report rather than blocking."""
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.side_effect = Exception("Bedrock timeout")
            result = await verify_risk(
                tool_name="GMAIL_SEND",
                tool_args={},
                self_reported_risk=RiskLevel.HIGH,
                justification="Sending email",
            )

        assert result["verified_risk"] == RiskLevel.HIGH
        assert "error" in result["reasoning"].lower() or "fallback" in result["reasoning"].lower()

    async def test_haiku_connection_error_falls_back(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.side_effect = ConnectionError("No route to Bedrock")
            result = await verify_risk(
                tool_name="TOOL",
                tool_args={},
                self_reported_risk=RiskLevel.CRITICAL,
                justification="test",
            )

        assert result["verified_risk"] == RiskLevel.CRITICAL

    async def test_haiku_returns_invalid_risk_string_falls_back(self):
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

    async def test_haiku_returns_missing_verified_risk_falls_back(self):
        """If Haiku's response is malformed, fall back."""
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {"reasoning": "I forgot the risk field"}
            result = await verify_risk(
                tool_name="TOOL",
                tool_args={},
                self_reported_risk=RiskLevel.HIGH,
                justification="test",
            )

        assert result["verified_risk"] == RiskLevel.HIGH

    async def test_haiku_returns_empty_dict_falls_back(self):
        with patch("nightowl.hitl.classifier._call_haiku", new_callable=AsyncMock) as mock_haiku:
            mock_haiku.return_value = {}
            result = await verify_risk(
                tool_name="TOOL",
                tool_args={},
                self_reported_risk=RiskLevel.MEDIUM,
                justification="test",
            )

        assert result["verified_risk"] == RiskLevel.MEDIUM
        assert isinstance(result["reasoning"], str)

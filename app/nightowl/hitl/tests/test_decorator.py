"""Tests for the @hitl_gated decorator.

Module under test: nightowl/hitl/decorator.py

The decorator wraps any Pydantic AI tool function to:
1. Extract risk_level + risk_justification from kwargs
2. Parse risk_level string → RiskLevel enum
3. HIGH/CRITICAL → skip classifier, go straight to HITL gate
4. LOW/MEDIUM → run Haiku classifier, then gate if verified >= MEDIUM
5. Denied → return denial string, never call the wrapped tool
6. Approved (or verified LOW) → call the wrapped tool

This is the critical glue between tools and the HITL system. If it breaks,
gated tools either run ungated or are permanently blocked.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nightowl.hitl.decorator import hitl_gated
from nightowl.hitl.gate import HITLGate
from nightowl.models.approval import ApprovalDecision, ApprovalResult, RiskLevel
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.tools import AgentState


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


@dataclass
class _FakeCtx:
    deps: AgentState


async def _make_ctx_with_gate(
    manager: SessionManager,
    gate: HITLGate | MagicMock | None = None,
) -> _FakeCtx:
    session = await manager.create_main_session("test")
    state = AgentState(session_id=session.id, manager=manager, hitl_gate=gate)
    return _FakeCtx(deps=state)


# A simple tool to decorate in tests
@hitl_gated
async def _dummy_tool(ctx: Any, query: str = "default") -> str:
    return f"executed:{query}"


# A tool that we can check was never called
_spy_tool_inner = AsyncMock(return_value="spy_result")


@hitl_gated
async def _spy_tool(ctx: Any, action: str = "go") -> str:
    return await _spy_tool_inner(action=action)


# ---------------------------------------------------------------------------
# Risk param extraction: risk_level and risk_justification stripped from kwargs
# ---------------------------------------------------------------------------


class TestRiskParamExtraction:
    async def test_risk_level_stripped_from_kwargs(self, manager: SessionManager):
        """The wrapped tool should NOT receive risk_level in its kwargs."""
        received_kwargs = {}

        @hitl_gated
        async def capture_tool(ctx, **kwargs):
            received_kwargs.update(kwargs)
            return "ok"

        ctx = await _make_ctx_with_gate(manager)
        with patch("nightowl.hitl.decorator._default_verify_risk", new_callable=AsyncMock) as mock:
            mock.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            await capture_tool(ctx, query="test", risk_level="low", risk_justification="safe")

        assert "risk_level" not in received_kwargs
        assert "risk_justification" not in received_kwargs
        assert received_kwargs["query"] == "test"

    async def test_defaults_to_low_when_risk_level_omitted(self, manager: SessionManager):
        """If the LLM doesn't provide risk_level, it should default to 'low'."""
        ctx = await _make_ctx_with_gate(manager)
        with patch("nightowl.hitl.decorator._default_verify_risk", new_callable=AsyncMock) as mock:
            mock.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            result = await _dummy_tool(ctx, query="hello")

        assert result == "executed:hello"


# ---------------------------------------------------------------------------
# Risk level parsing
# ---------------------------------------------------------------------------


class TestRiskLevelParsing:
    async def test_valid_risk_strings_accepted(self, manager: SessionManager):
        """All four risk level strings should parse without error."""
        for risk in ("low", "medium", "high", "critical"):
            ctx = await _make_ctx_with_gate(
                manager,
                gate=MagicMock(
                    request_approval=AsyncMock(
                        return_value=ApprovalResult(decision=ApprovalDecision.APPROVE),
                    ),
                ),
            )
            with patch("nightowl.hitl.decorator._default_verify_risk", new_callable=AsyncMock) as mock:
                mock.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
                result = await _dummy_tool(ctx, risk_level=risk, risk_justification="test")
            assert "executed" in result or "Error" not in result

    async def test_uppercase_risk_level_accepted(self, manager: SessionManager):
        ctx = await _make_ctx_with_gate(manager)
        with patch("nightowl.hitl.decorator._default_verify_risk", new_callable=AsyncMock) as mock:
            mock.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            result = await _dummy_tool(ctx, risk_level="LOW", risk_justification="safe")
        assert "executed" in result

    async def test_whitespace_risk_level_accepted(self, manager: SessionManager):
        ctx = await _make_ctx_with_gate(manager)
        with patch("nightowl.hitl.decorator._default_verify_risk", new_callable=AsyncMock) as mock:
            mock.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            result = await _dummy_tool(ctx, risk_level="  medium  ", risk_justification="")
        # Should not error on whitespace
        assert "invalid" not in result.lower()

    async def test_invalid_risk_level_returns_error_without_calling_tool(self, manager: SessionManager):
        received = []

        @hitl_gated
        async def tracked_tool(ctx, **kwargs):
            received.append(True)
            return "ran"

        ctx = await _make_ctx_with_gate(manager)
        result = await tracked_tool(ctx, risk_level="banana")

        assert "invalid" in result.lower() or "error" in result.lower()
        assert len(received) == 0  # tool must NOT have been called


# ---------------------------------------------------------------------------
# HIGH/CRITICAL: skip classifier, go straight to HITL gate
# ---------------------------------------------------------------------------


class TestHighCriticalSkipsClassifier:
    async def test_high_risk_does_not_call_classifier(self, manager: SessionManager):
        gate = MagicMock(
            request_approval=AsyncMock(return_value=ApprovalResult(decision=ApprovalDecision.APPROVE)),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)

        with patch("nightowl.hitl.decorator._default_verify_risk") as mock_verify:
            await _dummy_tool(ctx, risk_level="high", risk_justification="dangerous")

        mock_verify.assert_not_called()

    async def test_critical_risk_does_not_call_classifier(self, manager: SessionManager):
        gate = MagicMock(
            request_approval=AsyncMock(return_value=ApprovalResult(decision=ApprovalDecision.APPROVE)),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)

        with patch("nightowl.hitl.decorator._default_verify_risk") as mock_verify:
            await _dummy_tool(ctx, risk_level="critical", risk_justification="payment")

        mock_verify.assert_not_called()

    async def test_high_risk_goes_straight_to_gate(self, manager: SessionManager):
        gate = MagicMock(
            request_approval=AsyncMock(return_value=ApprovalResult(decision=ApprovalDecision.APPROVE)),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)

        with patch("nightowl.hitl.decorator._default_verify_risk"):
            await _dummy_tool(ctx, risk_level="high", risk_justification="send email")

        gate.request_approval.assert_called_once()

    async def test_critical_risk_goes_straight_to_gate(self, manager: SessionManager):
        gate = MagicMock(
            request_approval=AsyncMock(return_value=ApprovalResult(decision=ApprovalDecision.APPROVE)),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)

        with patch("nightowl.hitl.decorator._default_verify_risk"):
            await _dummy_tool(ctx, risk_level="critical", risk_justification="delete data")

        gate.request_approval.assert_called_once()


# ---------------------------------------------------------------------------
# LOW/MEDIUM: run classifier, then gate if verified >= MEDIUM
# ---------------------------------------------------------------------------


class TestLowMediumRunsClassifier:
    async def test_low_risk_runs_classifier(self, manager: SessionManager):
        ctx = await _make_ctx_with_gate(manager)

        with patch("nightowl.hitl.decorator._default_verify_risk", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            await _dummy_tool(ctx, risk_level="low", risk_justification="read-only")

        mock_verify.assert_called_once()

    async def test_medium_risk_runs_classifier(self, manager: SessionManager):
        gate = MagicMock(
            request_approval=AsyncMock(return_value=ApprovalResult(decision=ApprovalDecision.APPROVE)),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)

        with patch("nightowl.hitl.decorator._default_verify_risk", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"verified_risk": RiskLevel.MEDIUM, "reasoning": "ok"}
            await _dummy_tool(ctx, risk_level="medium", risk_justification="create event")

        mock_verify.assert_called_once()

    async def test_classifier_receives_tool_name(self, manager: SessionManager):
        ctx = await _make_ctx_with_gate(manager)

        with patch("nightowl.hitl.decorator._default_verify_risk", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            await _dummy_tool(ctx, risk_level="low", risk_justification="test")

        call_str = str(mock_verify.call_args)
        assert "_dummy_tool" in call_str

    async def test_classifier_receives_tool_kwargs(self, manager: SessionManager):
        ctx = await _make_ctx_with_gate(manager)

        with patch("nightowl.hitl.decorator._default_verify_risk", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            await _dummy_tool(ctx, query="find restaurants", risk_level="low", risk_justification="")

        call_str = str(mock_verify.call_args)
        assert "find restaurants" in call_str


# ---------------------------------------------------------------------------
# Classifier upgrade: LOW reported → verified HIGH → must gate
# ---------------------------------------------------------------------------


class TestClassifierUpgradeTriggersGate:
    async def test_low_upgraded_to_high_triggers_gate(self, manager: SessionManager):
        gate = MagicMock(
            request_approval=AsyncMock(return_value=ApprovalResult(decision=ApprovalDecision.APPROVE)),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)

        with patch("nightowl.hitl.decorator._default_verify_risk", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"verified_risk": RiskLevel.HIGH, "reasoning": "actually sends money"}
            await _dummy_tool(ctx, risk_level="low", risk_justification="safe")

        gate.request_approval.assert_called_once()

    async def test_low_upgraded_to_medium_triggers_gate(self, manager: SessionManager):
        gate = MagicMock(
            request_approval=AsyncMock(return_value=ApprovalResult(decision=ApprovalDecision.APPROVE)),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)

        with patch("nightowl.hitl.decorator._default_verify_risk", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"verified_risk": RiskLevel.MEDIUM, "reasoning": "creates data"}
            await _dummy_tool(ctx, risk_level="low", risk_justification="safe")

        gate.request_approval.assert_called_once()

    async def test_low_confirmed_low_skips_gate(self, manager: SessionManager):
        gate = MagicMock(
            request_approval=AsyncMock(return_value=ApprovalResult(decision=ApprovalDecision.APPROVE)),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)

        with patch("nightowl.hitl.decorator._default_verify_risk", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "read-only"}
            await _dummy_tool(ctx, risk_level="low", risk_justification="safe")

        gate.request_approval.assert_not_called()


# ---------------------------------------------------------------------------
# Approval outcome: approved → execute, denied → denial string
# ---------------------------------------------------------------------------


class TestApprovalOutcome:
    async def test_approved_calls_wrapped_tool(self, manager: SessionManager):
        gate = MagicMock(
            request_approval=AsyncMock(return_value=ApprovalResult(decision=ApprovalDecision.APPROVE)),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)

        result = await _dummy_tool(ctx, query="go", risk_level="high", risk_justification="test")

        assert result == "executed:go"

    async def test_denied_returns_denial_string(self, manager: SessionManager):
        gate = MagicMock(
            request_approval=AsyncMock(
                return_value=ApprovalResult(
                    decision=ApprovalDecision.REJECT,
                    reason="Too risky",
                ),
            ),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)

        result = await _dummy_tool(ctx, query="go", risk_level="high", risk_justification="test")

        assert "denied" in result.lower() or "rejected" in result.lower()
        assert "too risky" in result.lower()

    async def test_denied_never_calls_wrapped_tool(self, manager: SessionManager):
        gate = MagicMock(
            request_approval=AsyncMock(return_value=ApprovalResult(decision=ApprovalDecision.REJECT)),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)

        _spy_tool_inner.reset_mock()
        await _spy_tool(ctx, action="delete_everything", risk_level="critical", risk_justification="test")

        _spy_tool_inner.assert_not_called()

    async def test_redirect_returns_redirect_message_without_calling_tool(self, manager: SessionManager):
        gate = MagicMock(
            request_approval=AsyncMock(
                return_value=ApprovalResult(
                    decision=ApprovalDecision.REDIRECT,
                    redirect_message="Ask the user which account to use.",
                ),
            ),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)

        _spy_tool_inner.reset_mock()
        result = await _spy_tool(ctx, action="charge_card", risk_level="critical", risk_justification="test")

        assert result == ""
        _spy_tool_inner.assert_not_called()

    async def test_approved_passes_original_kwargs_to_tool(self, manager: SessionManager):
        received = {}

        @hitl_gated
        async def capture_tool(ctx, **kwargs):
            received.update(kwargs)
            return "ok"

        gate = MagicMock(
            request_approval=AsyncMock(return_value=ApprovalResult(decision=ApprovalDecision.APPROVE)),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)
        await capture_tool(ctx, query="restaurants", limit=5, risk_level="high", risk_justification="")

        assert received == {"query": "restaurants", "limit": 5}


# ---------------------------------------------------------------------------
# Gate receives correct arguments
# ---------------------------------------------------------------------------


class TestGateArguments:
    async def test_gate_receives_session_id(self, manager: SessionManager):
        gate = MagicMock(
            request_approval=AsyncMock(return_value=ApprovalResult(decision=ApprovalDecision.APPROVE)),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)

        await _dummy_tool(ctx, risk_level="high", risk_justification="test")

        call_kwargs = gate.request_approval.call_args
        call_str = str(call_kwargs)
        assert ctx.deps.session_id in call_str

    async def test_gate_receives_tool_name(self, manager: SessionManager):
        gate = MagicMock(
            request_approval=AsyncMock(return_value=ApprovalResult(decision=ApprovalDecision.APPROVE)),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)

        await _dummy_tool(ctx, risk_level="high", risk_justification="test")

        call_str = str(gate.request_approval.call_args)
        assert "_dummy_tool" in call_str

    async def test_gate_receives_verified_risk_level(self, manager: SessionManager):
        gate = MagicMock(
            request_approval=AsyncMock(return_value=ApprovalResult(decision=ApprovalDecision.APPROVE)),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)

        await _dummy_tool(ctx, risk_level="critical", risk_justification="test")

        call_str = str(gate.request_approval.call_args)
        assert "critical" in call_str.lower()

    async def test_gate_receives_justification_as_reason(self, manager: SessionManager):
        gate = MagicMock(
            request_approval=AsyncMock(return_value=ApprovalResult(decision=ApprovalDecision.APPROVE)),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)

        await _dummy_tool(ctx, risk_level="high", risk_justification="sending email to external recipient")

        gate.request_approval.assert_called_once()
        call_kwargs = gate.request_approval.call_args
        assert call_kwargs.kwargs.get("reason") == "sending email to external recipient"


# ---------------------------------------------------------------------------
# No gate configured: must deny by default (fail-closed)
# ---------------------------------------------------------------------------


class TestNoGateConfigured:
    async def test_no_gate_denies_by_default(self, manager: SessionManager):
        ctx = await _make_ctx_with_gate(manager, gate=None)

        result = await _dummy_tool(ctx, risk_level="high", risk_justification="test")

        assert "denied" in result.lower()

    async def test_no_gate_never_calls_tool(self, manager: SessionManager):
        ctx = await _make_ctx_with_gate(manager, gate=None)

        _spy_tool_inner.reset_mock()
        await _spy_tool(ctx, action="go", risk_level="high", risk_justification="test")

        _spy_tool_inner.assert_not_called()

    async def test_low_verified_still_runs_without_gate(self, manager: SessionManager):
        """LOW risk doesn't need a gate, so missing gate shouldn't block it."""
        ctx = await _make_ctx_with_gate(manager, gate=None)

        with patch("nightowl.hitl.decorator._default_verify_risk", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "safe"}
            result = await _dummy_tool(ctx, query="search", risk_level="low")

        assert result == "executed:search"


# ---------------------------------------------------------------------------
# Classifier failure fallback
# ---------------------------------------------------------------------------


class TestClassifierFailure:
    async def test_classifier_error_falls_back_to_self_reported(self, manager: SessionManager):
        """If the classifier throws, use the agent's self-reported risk."""
        gate = MagicMock(
            request_approval=AsyncMock(return_value=ApprovalResult(decision=ApprovalDecision.APPROVE)),
        )
        ctx = await _make_ctx_with_gate(manager, gate=gate)

        with patch("nightowl.hitl.decorator._default_verify_risk", new_callable=AsyncMock) as mock_verify:
            mock_verify.side_effect = Exception("Bedrock down")
            result = await _dummy_tool(ctx, risk_level="medium", risk_justification="test")

        # medium falls back → should gate (medium >= medium)
        gate.request_approval.assert_called_once()
        assert result == "executed:default"

    async def test_classifier_error_on_low_risk_still_executes(self, manager: SessionManager):
        """Classifier failure on LOW risk should still let the tool run."""
        ctx = await _make_ctx_with_gate(manager, gate=None)

        with patch("nightowl.hitl.decorator._default_verify_risk", new_callable=AsyncMock) as mock_verify:
            mock_verify.side_effect = Exception("Bedrock down")
            result = await _dummy_tool(ctx, query="search", risk_level="low")

        # low falls back to low → no gate needed → executes
        assert result == "executed:search"


# ---------------------------------------------------------------------------
# Wrapped tool error handling
# ---------------------------------------------------------------------------


class TestToolErrors:
    async def test_tool_exception_returns_error_string(self, manager: SessionManager):
        @hitl_gated
        async def broken_tool(ctx, **kwargs):
            raise RuntimeError("connection lost")

        ctx = await _make_ctx_with_gate(manager)
        with patch("nightowl.hitl.decorator._default_verify_risk", new_callable=AsyncMock) as mock:
            mock.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            result = await broken_tool(ctx, risk_level="low")

        assert "error" in result.lower()
        assert "connection lost" in result

    async def test_tool_exception_does_not_propagate(self, manager: SessionManager):
        @hitl_gated
        async def exploding_tool(ctx, **kwargs):
            raise ValueError("boom")

        ctx = await _make_ctx_with_gate(manager)
        with patch("nightowl.hitl.decorator._default_verify_risk", new_callable=AsyncMock) as mock:
            mock.return_value = {"verified_risk": RiskLevel.LOW, "reasoning": "ok"}
            # Must not raise — decorator catches it
            result = await exploding_tool(ctx, risk_level="low")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Decorator preserves function metadata
# ---------------------------------------------------------------------------


class TestDecoratorMetadata:
    def test_preserves_function_name(self):
        assert _dummy_tool.__name__ == "_dummy_tool"

    def test_preserves_wrapped_attribute(self):
        assert hasattr(_dummy_tool, "__wrapped__")

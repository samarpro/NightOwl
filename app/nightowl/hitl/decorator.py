"""HITL decorator — attach to any Pydantic AI tool to add risk classification and approval gating.

Usage:
    @hitl_gated
    async def my_tool(ctx: RunContext[AgentState], ..., risk_level: str = "low", risk_justification: str = "") -> ...:
        # pure tool logic, no HITL concerns

The decorator:
1. Extracts and strips risk_level + risk_justification from the call
2. Parses risk_level (lowercased, stripped)
3. HIGH/CRITICAL → straight to HITL approval (no classifier needed, already dangerous)
4. LOW/MEDIUM → runs Haiku classifier to catch underreported risk
5. If verified risk >= MEDIUM, requests approval via the HITLGate on ctx.deps
6. If denied, returns a denial string without calling the tool
7. If approved (or verified LOW), calls the wrapped tool
"""

from __future__ import annotations

import functools
import inspect
import logging
import sys
from typing import Any

from pydantic_ai import RunContext

from nightowl.hitl.classifier import verify_risk as _default_verify_risk
from nightowl.models.approval import ApprovalDecision, RiskLevel
from nightowl.sessions.tools import AgentState

log = logging.getLogger(__name__)


def hitl_gated(fn: Any) -> Any:
    """Decorator that wraps a Pydantic AI tool with HITL gating."""

    @functools.wraps(fn)
    async def wrapper(ctx: RunContext[AgentState], *args: Any, **kwargs: Any) -> Any:
        # Extract HITL params — the LLM provides these, but the tool doesn't need them
        raw_risk = kwargs.pop("risk_level", "low")
        justification = kwargs.pop("risk_justification", "")

        # Parse risk level
        try:
            parsed_risk = RiskLevel(str(raw_risk).strip().lower())
        except (ValueError, AttributeError):
            return f"Error: invalid risk_level '{raw_risk}'. Must be low, medium, high, or critical."

        # HIGH/CRITICAL — already dangerous, skip classifier, go straight to HITL
        # LOW/MEDIUM — run classifier to catch underreported risk
        if parsed_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            verified_risk = parsed_risk
        else:
            try:
                tool_name = fn.__name__
                tool_args = {k: v for k, v in kwargs.items()}
                # Resolve verify_risk from the wrapped function's module so
                # tests can patch it at the tool's import location.
                fn_module = sys.modules.get(fn.__module__)
                _verify_risk = getattr(fn_module, "verify_risk", _default_verify_risk)
                classification = await _verify_risk(
                    tool_name=tool_name,
                    tool_args=tool_args,
                    self_reported_risk=parsed_risk,
                    justification=justification,
                )
                verified_risk = classification["verified_risk"]
            except Exception:
                log.exception("Risk classifier failed, falling back to self-reported")
                verified_risk = parsed_risk

        # Gate — request approval for MEDIUM+
        if verified_risk != RiskLevel.LOW:
            gate = ctx.deps.hitl_gate
            if gate is None:
                log.warning("No HITL gate configured — denying %s by default", fn.__name__)
                return f"Action denied — no approval gate configured for {fn.__name__}."

            approval_result = await gate.request_approval(
                session_id=ctx.deps.session_id,
                tool_name=fn.__name__,
                tool_args={k: v for k, v in kwargs.items()},
                risk_level=verified_risk,
                reason=justification,
            )
            if approval_result.decision == ApprovalDecision.REJECT:
                reason_suffix = (
                    f" Reason: {approval_result.reason}" if approval_result.reason else ""
                )
                return f"Action denied — {fn.__name__} was rejected by the user.{reason_suffix}"
            if approval_result.decision == ApprovalDecision.REDIRECT:
                return ""

        # Approved or LOW — call the actual tool
        try:
            return await fn(ctx, *args, **kwargs)
        except Exception as exc:
            log.exception("Tool %s failed", fn.__name__)
            return f"Error in {fn.__name__}: {exc}"

    return wrapper

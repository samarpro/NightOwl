"""Haiku risk verification classifier.

Calls Claude Haiku via Bedrock to second-guess the agent's self-reported risk
level. Only runs when self_reported_risk >= MEDIUM. Fast pass to catch false
positives and flag underreported risk.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel

from nightowl.config import settings
from nightowl.models.approval import RiskLevel

log = logging.getLogger(__name__)

_HAIKU_MODEL = "au.anthropic.claude-haiku-4-5-20251001-v1:0"

_SYSTEM_PROMPT = """\
You are a risk classifier for an AI assistant's tool calls.
Given a tool name, its arguments, the agent's self-reported risk level,
and the agent's justification, verify whether the risk level is accurate.

Risk levels (low → critical):
- low: read-only, no side effects
- medium: creates/modifies data the user owns, reversible
- high: external communication, financial reads, irreversible writes
- critical: financial transactions, bulk deletes, account-level changes

IMPORTANT CONTEXT — sandbox tools:
Tools prefixed with "sandbox_", "bash_exec", "browser_", and "computer_use_" \
run inside ephemeral Docker containers that are destroyed after the session. \
They have NO access to the host filesystem, host network, or user credentials \
beyond what was explicitly injected. Running scripts, installing packages, \
writing files, or navigating websites inside these containers is inherently \
LOW risk. Only classify sandbox tool calls as medium+ if they explicitly \
perform external communication with real services (e.g. sending emails, \
posting to APIs with real credentials, making purchases).

Respond with ONLY a JSON object:
{"verified_risk": "<low|medium|high|critical>", "reasoning": "<one sentence>"}
"""


def _build_prompt(
    tool_name: str,
    tool_args: dict[str, Any],
    self_reported_risk: RiskLevel,
    justification: str,
    session_context: str | None = None,
) -> str:
    parts = [
        f"Tool: {tool_name}",
        f"Arguments: {json.dumps(tool_args)}",
        f"Agent-reported risk: {self_reported_risk.value}",
        f"Agent justification: {justification}",
    ]
    if session_context:
        parts.append(f"Session context: {session_context}")
    parts.append("\nVerify the risk level. Respond with JSON only.")
    return "\n".join(parts)


class RiskVerification(BaseModel):
    verified_risk: str
    reasoning: str


async def _call_haiku(system: str, prompt: str) -> dict[str, Any]:
    """Call Haiku via Bedrock with typed output."""
    from pydantic_ai import Agent
    from pydantic_ai.models.bedrock import BedrockConverseModel
    from nightowl.config import bedrock_provider

    model = BedrockConverseModel(model_name=_HAIKU_MODEL, provider=bedrock_provider())
    agent: Agent[None, RiskVerification] = Agent(
        model=model, system_prompt=system, output_type=RiskVerification,
    )
    result = await agent.run(prompt)
    return result.output.model_dump()


async def verify_risk(
    tool_name: str,
    tool_args: dict[str, Any],
    self_reported_risk: RiskLevel,
    justification: str,
    session_context: str | None = None,
) -> dict[str, Any]:
    """Verify the agent's self-reported risk level using Haiku.

    Returns {"verified_risk": RiskLevel, "reasoning": str}.
    Called for LOW and MEDIUM risk to catch underreported danger.
    HIGH/CRITICAL bypass the classifier entirely (handled by decorator).
    """
    prompt = _build_prompt(
        tool_name, tool_args, self_reported_risk, justification, session_context
    )

    try:
        raw = await _call_haiku(_SYSTEM_PROMPT, prompt)
        verified_str = raw.get("verified_risk", "")
        reasoning = raw.get("reasoning", "")

        # Parse into RiskLevel enum, fall back on invalid response
        try:
            verified_risk = RiskLevel(verified_str)
        except ValueError:
            log.warning(
                "Haiku returned invalid risk level %r, falling back to %s",
                verified_str,
                self_reported_risk,
            )
            return {
                "verified_risk": self_reported_risk,
                "reasoning": f"Fallback — Haiku returned invalid risk: {verified_str}",
            }

        return {"verified_risk": verified_risk, "reasoning": reasoning}

    except Exception:
        log.exception("Haiku classifier error, falling back to self-reported risk")
        return {
            "verified_risk": self_reported_risk,
            "reasoning": "Fallback — error calling Haiku classifier",
        }

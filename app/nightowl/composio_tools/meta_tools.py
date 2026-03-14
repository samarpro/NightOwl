"""Composio meta-tools for Pydantic AI agents.

composio_search_tools — discover available Composio tools by query.
composio_execute — execute a Composio tool with risk classification and HITL gating.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic_ai import RunContext

from nightowl.config import settings
from nightowl.hitl.classifier import verify_risk
from nightowl.models.approval import RiskLevel
from nightowl.sessions.tools import AgentState

log = logging.getLogger(__name__)


class _ComposioClient:
    """Thin wrapper around the Composio SDK for search and execute."""

    def __init__(self) -> None:
        from composio import Composio

        self._sdk = Composio(api_key=settings.composio_api_key)

    async def search_tools(self, query: str) -> list[dict[str, Any]]:
        raw = self._sdk.tools.get_raw_composio_tools(search=query, limit=20)
        return [{"name": t.slug, "description": t.description} for t in raw]

    async def execute_tool(
        self, tool_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        result = self._sdk.tools.execute(slug=tool_name, arguments=params)
        return {"status": "ok", "data": result}


_client_instance: _ComposioClient | None = None


def _get_composio_client() -> _ComposioClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = _ComposioClient()
    return _client_instance


async def _request_approval(
    session_id: str,
    tool_name: str,
    tool_args: dict[str, Any],
    risk_level: RiskLevel,
) -> bool:
    """Request HITL approval. Placeholder — wired to HITLGate in the gateway."""
    from nightowl.hitl.gate import HITLGate

    # In production this gate instance is provided by the app lifespan.
    # For now, this function exists as a seam the tests can patch.
    log.warning("_request_approval called outside gateway context")
    return False


async def composio_search_tools(
    ctx: RunContext[AgentState],
    query: str,
) -> list[dict[str, Any]] | str:
    """Search Composio for available tools matching a query.

    Returns a list of {name, description} dicts, or an error string on failure.
    """
    try:
        client = _get_composio_client()
        return await client.search_tools(query)
    except Exception as exc:
        log.exception("Composio search error")
        return f"Error searching Composio tools: {exc}"


async def composio_execute(
    ctx: RunContext[AgentState],
    tool_name: str,
    params: dict[str, Any],
    risk_level: str,
    risk_justification: str,
) -> dict[str, Any] | str:
    """Execute a Composio tool with risk classification and HITL gating.

    Flow:
    1. Parse risk_level string to RiskLevel enum
    2. If risk >= MEDIUM, run Haiku classifier to verify
    3. If verified risk >= MEDIUM, request HITL approval
    4. If approved (or low risk), execute via Composio
    5. If rejected, return denial message
    """
    parsed_risk = RiskLevel(risk_level)
    session_id = ctx.deps.session_id

    # Step 1: Classify risk (skipped for LOW)
    if parsed_risk != RiskLevel.LOW:
        classification = await verify_risk(
            tool_name=tool_name,
            tool_args=params,
            self_reported_risk=parsed_risk,
            justification=risk_justification,
        )
        verified_risk = classification["verified_risk"]
    else:
        verified_risk = RiskLevel.LOW

    # Step 2: HITL gate for MEDIUM+ verified risk
    if verified_risk != RiskLevel.LOW:
        approved = await _request_approval(
            session_id=session_id,
            tool_name=tool_name,
            tool_args=params,
            risk_level=verified_risk,
        )
        if not approved:
            return f"Action denied — {tool_name} was rejected by the user."

    # Step 3: Execute
    try:
        client = _get_composio_client()
        return await client.execute_tool(tool_name, params=params)
    except Exception as exc:
        log.exception("Composio execution error")
        return f"Error executing {tool_name}: {exc}"

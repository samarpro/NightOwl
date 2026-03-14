"""Composio meta-tools for Pydantic AI agents.

composio_search_tools — discover available Composio tools by query.
composio_execute — execute a Composio tool with HITL gating via decorator.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic_ai import RunContext

from nightowl.config import settings
from nightowl.hitl.decorator import hitl_gated
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


@hitl_gated
async def composio_execute(
    ctx: RunContext[AgentState],
    tool_name: str,
    params: dict[str, Any],
    risk_level: str = "low",
    risk_justification: str = "",
) -> dict[str, Any] | str:
    """Execute a Composio tool.

    Args:
        tool_name: The Composio tool slug to execute.
        params: Arguments to pass to the tool.
        risk_level: Self-assessed risk — "low", "medium", "high", or "critical".
        risk_justification: Why you chose this risk level.
    """
    client = _get_composio_client()
    return await client.execute_tool(tool_name, params=params)

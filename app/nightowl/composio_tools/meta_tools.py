"""Composio meta-tools for Pydantic AI agents.

composio_search_tools — discover available Composio tools by query.
composio_execute — execute a Composio tool with HITL gating via decorator.

Auth flow: when a tool execution fails due to missing connected account,
we initiate an OAuth flow, send the auth link to the user, and block until
Composio calls back to our webhook confirming the connection is active.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic_ai import RunContext

from nightowl.config import settings
from nightowl.hitl.decorator import hitl_gated
from nightowl.sessions.tools import AgentState

log = logging.getLogger(__name__)

_NO_ACCOUNT_SLUG = "ActionExecute_ConnectedAccountNotFound"
_ENTITY_ID_REQUIRED_SLUG = "ActionExecute_ConnectedAccountEntityIdRequired"

_AUTH_TIMEOUT = 300.0

NotifyUser = Callable[[str], Awaitable[None]]


class AuthWaiter:
    """Tracks pending OAuth flows and resolves them when Composio calls back."""

    def __init__(self) -> None:
        self._pending: dict[str, asyncio.Event] = {}

    def register(self, connection_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self._pending[connection_id] = event
        return event

    def resolve(self, connection_id: str) -> bool:
        event = self._pending.pop(connection_id, None)
        if event is None:
            return False
        event.set()
        return True


# Singleton — shared between the tool and the webhook router
auth_waiter = AuthWaiter()


class _ComposioClient:
    """Thin wrapper around the Composio SDK for search and execute."""

    def __init__(self) -> None:
        from composio import Composio

        self._sdk = Composio(api_key=settings.composio_api_key)
        self._version_cache: dict[str, str] = {}

    async def search_tools(self, query: str) -> list[dict[str, Any]]:
        raw = self._sdk.tools.get_raw_composio_tools(search=query, limit=20)
        tools = []
        for t in raw:
            self._version_cache[t.slug] = t.version
            tools.append({"name": t.slug, "description": t.description, "version": t.version})
        return tools

    def _resolve_version(self, tool_name: str) -> str | None:
        version = self._version_cache.get(tool_name)
        if version is None:
            hits = self._sdk.tools.get_raw_composio_tools(search=tool_name, limit=1)
            if hits:
                version = hits[0].version
                self._version_cache[tool_name] = version
        return version

    def _toolkit_from_slug(self, tool_name: str) -> str:
        return tool_name.split("_")[0].lower()

    def _initiate_connection(self, toolkit: str, callback_url: str | None = None) -> tuple[str, str]:
        """Start an OAuth flow. Returns (connection_id, redirect_url)."""
        configs = self._sdk.auth_configs.list(toolkit_slug=toolkit)
        if not configs.items:
            raise ValueError(f"No auth config found for toolkit {toolkit}")
        auth_config_id = configs.items[0].id
        kwargs: dict[str, Any] = {
            "user_id": settings.composio_user_id,
            "auth_config_id": auth_config_id,
        }
        if callback_url:
            kwargs["callback_url"] = callback_url
        connection = self._sdk.connected_accounts.initiate(**kwargs)
        return connection.id, connection.redirect_url

    async def _poll_connection(self, connection_id: str) -> bool:
        """Poll until the connection becomes ACTIVE or timeout. Used in CLI mode."""
        elapsed = 0.0
        while elapsed < _AUTH_TIMEOUT:
            await asyncio.sleep(3.0)
            elapsed += 3.0
            try:
                conn = self._sdk.client.connected_accounts.retrieve(nanoid=connection_id)
                if conn.status == "ACTIVE":
                    return True
            except Exception:
                log.debug("Poll check failed for %s", connection_id)
        return False

    @staticmethod
    def _is_no_connected_account(exc: Exception) -> bool:
        body = getattr(exc, "body", None)
        if not isinstance(body, dict):
            return False
        slug = body.get("error", {}).get("slug", "")
        return slug in (_NO_ACCOUNT_SLUG, _ENTITY_ID_REQUIRED_SLUG)

    async def execute_tool(
        self,
        tool_name: str,
        params: dict[str, Any],
        notify: NotifyUser | None = None,
        callback_url: str | None = None,
    ) -> dict[str, Any]:
        version = self._resolve_version(tool_name)
        try:
            result = self._sdk.tools.execute(
                slug=tool_name, arguments=params, version=version,
                user_id=settings.composio_user_id,
            )
            return {"status": "ok", "data": result}
        except Exception as exc:
            if not self._is_no_connected_account(exc):
                raise

            toolkit = self._toolkit_from_slug(tool_name)
            log.info("No connected account for %s, initiating auth flow", toolkit)
            connection_id, redirect_url = self._initiate_connection(toolkit, callback_url)

            msg = f"🔗 Authentication required for {toolkit}. Please open this link to connect your account:\n{redirect_url}"
            if notify:
                await notify(msg)
            else:
                print(f"\n  {msg}")

            log.info("Waiting for %s auth (connection %s)...", toolkit, connection_id)
            if callback_url:
                # Webhook mode: wait for Composio to call our callback
                event = auth_waiter.register(connection_id)
                try:
                    await asyncio.wait_for(event.wait(), timeout=_AUTH_TIMEOUT)
                except asyncio.TimeoutError:
                    auth_waiter._pending.pop(connection_id, None)
                    return {"status": "auth_timeout", "message": f"Authentication for {toolkit} timed out after {_AUTH_TIMEOUT}s."}
            else:
                # Poll mode (CLI, no server): check connection status periodically
                connected = await self._poll_connection(connection_id)
                if not connected:
                    return {"status": "auth_timeout", "message": f"Authentication for {toolkit} timed out after {_AUTH_TIMEOUT}s."}

            log.info("Auth completed for %s, retrying tool", toolkit)
            result = self._sdk.tools.execute(
                slug=tool_name, arguments=params, version=version,
                user_id=settings.composio_user_id,
            )
            return {"status": "ok", "data": result}


_client_instance: _ComposioClient | None = None


def _get_composio_client() -> _ComposioClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = _ComposioClient()
    return _client_instance


async def _build_notify(ctx: RunContext[AgentState]) -> NotifyUser | None:
    registry = ctx.deps.channel_registry
    if registry is None:
        return None
    session_id = ctx.deps.session_id

    async def notify(text: str) -> None:
        await registry.send_session_reply(session_id, text)

    return notify


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
    notify = await _build_notify(ctx)
    callback_url = f"{settings.public_url}/api/v1/composio/auth/callback" if settings.public_url else None
    return await client.execute_tool(tool_name, params=params, notify=notify, callback_url=callback_url)

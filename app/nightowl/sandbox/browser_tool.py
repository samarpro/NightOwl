"""Browser tools — Pydantic AI tools for Playwright-based browsing inside a sandbox container.

All commands are serialised as JSON and executed via a helper script inside
the browser container, which runs headless Chromium + Playwright.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic_ai import RunContext

from nightowl.hitl.classifier import verify_risk
from nightowl.hitl.decorator import hitl_gated
from nightowl.models.session import SandboxMode
from nightowl.sessions.tools import AgentState


async def _ensure_browser_container(ctx: RunContext[AgentState]) -> tuple[Any, str] | str:
    """Ensure a browser container exists. Returns (manager, container_id) or error string."""
    sandbox_mgr = getattr(ctx.deps, "sandbox_manager", None)
    if sandbox_mgr is None:
        return "Error: no sandbox manager configured for this session."
    container_id = await sandbox_mgr.ensure_container(ctx.deps.session_id, SandboxMode.BROWSER)
    return sandbox_mgr, container_id


@hitl_gated
async def browser_navigate(
    ctx: RunContext[AgentState],
    url: str,
) -> str:
    """Navigate the browser to a URL and return the page snapshot.

    A browser container (headless Chromium + Playwright) is created
    automatically on first use.

    Args:
        url: The URL to navigate to.
    """
    result = await _ensure_browser_container(ctx)
    if isinstance(result, str):
        return result
    sandbox_mgr, container_id = result

    cmd = json.dumps({"action": "navigate", "url": url})
    exec_result = await sandbox_mgr.exec_command(container_id, f"playwright-bridge '{cmd}'")

    if exec_result.exit_code != 0:
        return f"Error navigating to {url}: {exec_result.stderr or exec_result.stdout}"
    return exec_result.stdout


@hitl_gated
async def browser_interact(
    ctx: RunContext[AgentState],
    selector: str,
    action: str,
    value: str | None = None,
) -> str:
    """Interact with a page element — click, fill, select, etc.

    Args:
        selector: CSS selector for the target element.
        action: The interaction type (click, fill, select, etc.).
        value: Optional value for fill/select actions.
    """
    result = await _ensure_browser_container(ctx)
    if isinstance(result, str):
        return result
    sandbox_mgr, container_id = result

    payload: dict[str, Any] = {"action": action, "selector": selector}
    if value is not None:
        payload["value"] = value
    cmd = json.dumps(payload)
    exec_result = await sandbox_mgr.exec_command(container_id, f"playwright-bridge '{cmd}'")

    if exec_result.exit_code != 0:
        return f"Error interacting with {selector}: {exec_result.stderr or exec_result.stdout}"
    return exec_result.stdout


@hitl_gated
async def browser_screenshot(
    ctx: RunContext[AgentState],
) -> str:
    """Take a screenshot of the current browser page.

    Returns base64-encoded image data.
    """
    result = await _ensure_browser_container(ctx)
    if isinstance(result, str):
        return result
    sandbox_mgr, container_id = result

    cmd = json.dumps({"action": "screenshot"})
    exec_result = await sandbox_mgr.exec_command(container_id, f"playwright-bridge '{cmd}'")

    if exec_result.exit_code != 0:
        return f"Error taking screenshot: {exec_result.stderr or exec_result.stdout}"
    return exec_result.stdout

"""Computer use tools — screenshot and mouse/keyboard actions via VNC inside the computer_use container."""

from __future__ import annotations

import json
from typing import Any

from pydantic_ai import RunContext

from nightowl.hitl.classifier import verify_risk
from nightowl.hitl.decorator import hitl_gated
from nightowl.models.session import SandboxMode
from nightowl.sessions.tools import AgentState


async def _ensure_computer_container(ctx: RunContext[AgentState]) -> tuple[Any, str] | str:
    """Ensure a computer-use container exists. Returns (manager, container_id) or error string."""
    sandbox_mgr = getattr(ctx.deps, "sandbox_manager", None)
    if sandbox_mgr is None:
        return "Error: no sandbox manager configured for this session."
    container_id = await sandbox_mgr.ensure_container(ctx.deps.session_id, SandboxMode.COMPUTER)
    return sandbox_mgr, container_id


@hitl_gated
async def computer_use_screenshot(
    ctx: RunContext[AgentState],
) -> str:
    """Capture a screenshot of the desktop environment.

    A computer-use container (Xvfb + VNC) is created automatically on
    first use. Returns base64-encoded screenshot data.
    """
    result = await _ensure_computer_container(ctx)
    if isinstance(result, str):
        return result
    sandbox_mgr, container_id = result

    cmd = json.dumps({"action": "screenshot"})
    exec_result = await sandbox_mgr.exec_command(container_id, f"computer-use-bridge '{cmd}'")

    if exec_result.exit_code != 0:
        return f"Error capturing screenshot: {exec_result.stderr or exec_result.stdout}"
    return exec_result.stdout


@hitl_gated
async def computer_use_action(
    ctx: RunContext[AgentState],
    action: str,
    coords: list[int] | None = None,
    text: str | None = None,
) -> str:
    """Send a mouse or keyboard action to the desktop environment.

    Args:
        action: The action type — click, type, scroll, double_click, etc.
        coords: [x, y] coordinates for mouse actions.
        text: Text to type for keyboard actions.
    """
    result = await _ensure_computer_container(ctx)
    if isinstance(result, str):
        return result
    sandbox_mgr, container_id = result

    payload: dict[str, Any] = {"action": action}
    if coords is not None:
        payload["coords"] = coords
    if text is not None:
        payload["text"] = text
    cmd = json.dumps(payload)
    exec_result = await sandbox_mgr.exec_command(container_id, f"computer-use-bridge '{cmd}'")

    if exec_result.exit_code != 0:
        return f"Error performing {action}: {exec_result.stderr or exec_result.stdout}"
    return exec_result.stdout

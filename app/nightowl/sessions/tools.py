"""Pydantic AI tool functions for session management.

These are registered on the agent and use RunContext to access session state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import RunContext

from nightowl.models.session import SandboxMode, Session, SpawnRequest
from nightowl.sessions.manager import SessionManager


@dataclass
class AgentState:
    session_id: str
    manager: SessionManager
    hitl_gate: Any = None  # Optional HITLGate instance
    channel_registry: Any = None  # Optional ChannelRegistry instance
    mcp_servers: list[Any] = field(default_factory=list)


async def sessions_spawn(
    ctx: RunContext[AgentState],
    task: str,
    label: str | None = None,
    sandbox: str | None = None,
    model: str | None = None,
) -> str:
    """Spawn a child agent session to work on a sub-task in parallel.

    Returns immediately with the child session ID. The child's result will
    arrive later as a completion message — do NOT poll or call sessions_list
    to wait for it.

    Args:
        task: What the child agent should do.
        label: Short name for this child (shown in dashboard).
        sandbox: Sandbox mode — "none", "cli", "browser", or "computer".
        model: Optional model override for this child (e.g. "anthropic.claude-haiku-4-5-v1").
    """
    try:
        manager = ctx.deps.manager
        sandbox_mode = SandboxMode(sandbox) if sandbox else SandboxMode.NONE
        request = SpawnRequest(task=task, label=label, sandbox=sandbox_mode, model=model)
        child = await manager.spawn_child(ctx.deps.session_id, request)
        return (
            f"Spawned child session {child.id} (role={child.role}, depth={child.depth})."
            f" Wait for the completion event — do NOT poll."
        )
    except Exception as exc:
        return f"Error spawning child session: {exc}"


async def sessions_list(ctx: RunContext[AgentState]) -> list[dict[str, Any]]:
    """List child sessions and their current status."""
    manager = ctx.deps.manager
    children = manager.list_children(ctx.deps.session_id)
    return [
        {
            "id": c.id,
            "label": c.label,
            "role": c.role.value,
            "state": c.state.value,
            "task": c.task,
        }
        for c in children
    ]


async def sessions_send(
    ctx: RunContext[AgentState], session_id: str, message: str
) -> str:
    """Send a steering message to a running child session."""
    manager = ctx.deps.manager
    child = manager.get_session(session_id)
    if child is None:
        return f"Session {session_id} not found."
    if child.parent_id != ctx.deps.session_id:
        return f"Session {session_id} is not your child."
    await manager.send_to_session(session_id, message)
    return f"Message sent to {session_id}."

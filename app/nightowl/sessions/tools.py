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
    store: Any = None  # Optional SessionStore instance
    skill_store: Any = None  # Optional SkillStore instance
    mcp_servers: list[Any] = field(default_factory=list)
    sandbox_manager: Any = None  # Optional DockerSandboxManager instance


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
    """Send a message to another session — a child, or your parent.

    Use this to steer a running child, ask your parent for clarification,
    or send progress updates. The target must be your child or your parent.

    Args:
        session_id: The session to send to.
        message: The message content.
    """
    manager = ctx.deps.manager
    me = manager.get_session(ctx.deps.session_id)
    target = manager.get_session(session_id)
    if target is None:
        return f"Session {session_id} not found."

    # Allow sending to children or parent
    is_child = target.parent_id == ctx.deps.session_id
    is_parent = me is not None and me.parent_id == session_id
    if not is_child and not is_parent:
        return f"Session {session_id} is not your child or parent."

    if is_child:
        label = me.label or ctx.deps.session_id if me else ctx.deps.session_id
        prefix = (
            f"[SYSTEM: MESSAGE FROM PARENT AGENT — {label}]\n"
            f"Your parent agent is sending you the following instruction or message.\n"
            f"---\n"
        )
    else:
        label = me.label or ctx.deps.session_id if me else ctx.deps.session_id
        prefix = (
            f"[SYSTEM: MESSAGE FROM CHILD AGENT — {label}]\n"
            f"The user CANNOT see this. You must relay relevant content to the user.\n"
            f"---\n"
        )
    await manager.send_to_session(session_id, prefix + message + "\n---")
    direction = "child" if is_child else "parent"
    return f"Message sent to {direction} {session_id}."


async def sessions_complete(
    ctx: RunContext[AgentState], session_id: str, reason: str = "",
) -> str:
    """Tell a child session to wrap up and complete.

    The child will finish its current work and exit. Use this when
    you're satisfied with the child's output and no longer need it.

    Args:
        session_id: The child session to complete.
        reason: Optional reason for completion.
    """
    manager = ctx.deps.manager
    target = manager.get_session(session_id)
    if target is None:
        return f"Session {session_id} not found."
    if target.parent_id != ctx.deps.session_id:
        return f"Session {session_id} is not your child."

    result = reason or "Completed by parent"
    await manager.complete_session(session_id, result)
    return f"Child session {session_id} completed."

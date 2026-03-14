"""bash_exec — Pydantic AI tool for running shell commands inside a sandbox container."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from nightowl.hitl.classifier import verify_risk
from nightowl.hitl.decorator import hitl_gated
from nightowl.models.session import SandboxMode
from nightowl.sessions.tools import AgentState


@hitl_gated
async def bash_exec(
    ctx: RunContext[AgentState],
    command: str,
) -> str:
    """Execute a shell command inside a sandboxed Docker container.

    A CLI container is created automatically on first use. Returns stdout
    on success, or stderr + exit code on failure.

    Args:
        command: The shell command to run.
    """
    sandbox_mgr = getattr(ctx.deps, "sandbox_manager", None)
    if sandbox_mgr is None:
        return "Error: no sandbox manager configured for this session."

    container_id = await sandbox_mgr.ensure_container(ctx.deps.session_id, SandboxMode.CLI)
    result = await sandbox_mgr.exec_command(container_id, command)

    if result.exit_code == 0:
        return result.stdout
    else:
        parts = []
        if result.stderr:
            parts.append(result.stderr)
        if result.stdout:
            parts.append(result.stdout)
        parts.append(f"[exit code: {result.exit_code}]")
        return "\n".join(parts)

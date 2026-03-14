"""File tools — read and write files inside sandbox containers.

These are low-risk tools that don't need HITL gating. Reading is read-only,
writing is contained inside an ephemeral Docker container.
"""

from __future__ import annotations

import base64
import json
from typing import Any

from pydantic_ai import RunContext

from nightowl.models.session import SandboxMode
from nightowl.sessions.tools import AgentState


async def _ensure_container(ctx: RunContext[AgentState]) -> tuple[Any, str] | str:
    sandbox_mgr = getattr(ctx.deps, "sandbox_manager", None)
    if sandbox_mgr is None:
        return "Error: no sandbox manager configured for this session."
    container_id = await sandbox_mgr.ensure_container(ctx.deps.session_id, SandboxMode.CLI)
    return sandbox_mgr, container_id


async def sandbox_read(
    ctx: RunContext[AgentState],
    path: str,
    offset: int | None = None,
    limit: int | None = None,
) -> str:
    """Read a file from the sandbox container.

    Returns the file contents with line numbers. For large files, use offset
    and limit to read a specific range.

    Args:
        path: Absolute path to the file inside the container.
        offset: Line number to start reading from (1-based). Omit to start from the beginning.
        limit: Maximum number of lines to read. Omit to read the entire file.
    """
    result = await _ensure_container(ctx)
    if isinstance(result, str):
        return result
    sandbox_mgr, container_id = result

    # Build a command that mimics cat -n with optional offset/limit
    if offset is not None and limit is not None:
        cmd = f"sed -n '{offset},{offset + limit - 1}p' {_quote(path)} | cat -n | sed 's/^ *//' | awk '{{printf \"%*d\\t%s\\n\", 6, NR + {offset - 1}, $0}}'"
        # Simpler approach: use tail + head
        cmd = f"tail -n +{offset} {_quote(path)} | head -n {limit} | awk '{{ printf \"%6d\\t%s\\n\", NR + {offset - 1}, $0 }}'"
    elif offset is not None:
        cmd = f"tail -n +{offset} {_quote(path)} | awk '{{ printf \"%6d\\t%s\\n\", NR + {offset - 1}, $0 }}'"
    elif limit is not None:
        cmd = f"head -n {limit} {_quote(path)} | awk '{{ printf \"%6d\\t%s\\n\", NR, $0 }}'"
    else:
        cmd = f"cat -n {_quote(path)}"

    exec_result = await sandbox_mgr.exec_command(container_id, cmd)

    if exec_result.exit_code != 0:
        return f"Error reading {path}: {exec_result.stderr or exec_result.stdout}"
    return exec_result.stdout


async def sandbox_write(
    ctx: RunContext[AgentState],
    path: str,
    content: str,
) -> str:
    """Write a file to the sandbox container. Creates parent directories if needed.

    Overwrites the file if it already exists. Use sandbox_read first if you
    need to preserve existing content.

    Args:
        path: Absolute path to the file inside the container.
        content: The full file content to write.
    """
    result = await _ensure_container(ctx)
    if isinstance(result, str):
        return result
    sandbox_mgr, container_id = result

    # Base64 encode to avoid any quoting/escaping issues
    encoded = base64.b64encode(content.encode()).decode()

    cmd = (
        f"mkdir -p $(dirname {_quote(path)}) && "
        f"echo '{encoded}' | base64 -d > {_quote(path)}"
    )
    exec_result = await sandbox_mgr.exec_command(container_id, cmd)

    if exec_result.exit_code != 0:
        return f"Error writing {path}: {exec_result.stderr or exec_result.stdout}"

    # Confirm with line count
    wc_result = await sandbox_mgr.exec_command(container_id, f"wc -l < {_quote(path)}")
    lines = wc_result.stdout.strip() if wc_result.exit_code == 0 else "?"
    return f"Wrote {path} ({lines} lines)"


async def sandbox_ls(
    ctx: RunContext[AgentState],
    path: str = ".",
    glob_pattern: str | None = None,
) -> str:
    """List files and directories in the sandbox container.

    Args:
        path: Directory to list. Defaults to the current working directory.
        glob_pattern: Optional glob pattern to filter results (e.g. "*.py", "src/**/*.ts").
    """
    result = await _ensure_container(ctx)
    if isinstance(result, str):
        return result
    sandbox_mgr, container_id = result

    if glob_pattern:
        cmd = f"find {_quote(path)} -path {_quote(glob_pattern)} -type f 2>/dev/null | head -200 | sort"
    else:
        cmd = f"ls -la {_quote(path)}"

    exec_result = await sandbox_mgr.exec_command(container_id, cmd)

    if exec_result.exit_code != 0:
        return f"Error listing {path}: {exec_result.stderr or exec_result.stdout}"
    return exec_result.stdout


def _quote(path: str) -> str:
    """Shell-quote a path to prevent injection."""
    return "'" + path.replace("'", "'\\''") + "'"

"""Slash command handling for inbound user messages.

Intercepts /command messages before they reach the agent. Returns a
CommandResult if the message was handled, or None if it should be
forwarded to the agent as a normal message.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from nightowl.models.session import SessionState

log = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result of a slash command. reply is sent back to the user's channel."""

    reply: str
    end_session: bool = False


async def handle_command(
    text: str,
    session_id: str,
    manager: Any,
    workers: dict[str, Any],
) -> CommandResult | None:
    """Parse and execute a slash command. Returns None if text is not a command."""
    stripped = text.strip()
    if not stripped.startswith("/"):
        return None

    parts = stripped.split(maxsplit=1)
    command = parts[0].lower()
    # arg = parts[1] if len(parts) > 1 else ""

    if command == "/clear":
        return await _cmd_clear(session_id, manager, workers)
    if command == "/new":
        return await _cmd_new(session_id, manager, workers)
    if command == "/status":
        return await _cmd_status(session_id, manager)
    if command == "/help":
        return _cmd_help()

    return None  # Unknown slash — pass through to agent


async def _cmd_clear(
    session_id: str, manager: Any, workers: dict[str, Any],
) -> CommandResult:
    """Clear the session: complete all children, wipe message history, reset runtime."""
    # Complete all active child sessions (recursively) so frontend sees them disappear
    await _complete_children_recursive(session_id, manager)

    # Clear the parent's tracking state
    session = manager.get_session(session_id)
    if session is not None:
        session.children.clear()
        session.expected_completions.clear()

    # Clear DB messages
    if manager.store:
        await manager.store.clear_messages(session_id)

    # Reset in-memory runtime history
    worker = workers.get(session_id)
    if worker is not None:
        runtime = worker.runtime
        runtime.message_history = []
        runtime.persisted_count = 0

    # Emit cleared event so the frontend can reset the canvas
    await manager._emit({
        "type": "session:cleared",
        "session_id": session_id,
    })

    log.info("Cleared session %s (history + children)", session_id)
    return CommandResult(reply="Session cleared.")


async def _complete_children_recursive(session_id: str, manager: Any) -> None:
    """Walk the session tree depth-first and complete all active children."""
    children = manager.list_children(session_id)
    for child in children:
        # Recurse into grandchildren first
        await _complete_children_recursive(child.id, manager)
        if child.state not in (SessionState.COMPLETED, SessionState.FAILED):
            try:
                await manager.complete_session(child.id, result="Cleared by user via /clear")
            except ValueError:
                pass  # already gone
        # Clean up in-memory state
        await manager.cleanup_session(child.id)


async def _cmd_new(
    session_id: str, manager: Any, workers: dict[str, Any],
) -> CommandResult:
    """End the current session so the next message starts a fresh one."""
    await manager.complete_session(session_id, result="Ended by user via /new")

    # Cancel the worker task
    worker = workers.pop(session_id, None)
    if worker is not None:
        worker.task.cancel()

    log.info("User ended session %s via /new", session_id)
    return CommandResult(reply="Session ended. Send a new message to start fresh.", end_session=True)


async def _cmd_status(session_id: str, manager: Any) -> CommandResult:
    """Report current session state and children."""
    session = manager.get_session(session_id)
    if session is None:
        return CommandResult(reply="No active session.")

    children = manager.list_children(session_id)
    lines = [
        f"Session: {session.id}",
        f"State: {session.state.value}",
        f"Depth: {session.depth}",
    ]
    if children:
        lines.append(f"Children ({len(children)}):")
        for child in children:
            label = child.label or child.id
            lines.append(f"  - {label}: {child.state.value}")
    else:
        lines.append("No active children.")

    pending = len(session.expected_completions)
    if pending:
        lines.append(f"Waiting on {pending} child completion(s).")

    return CommandResult(reply="\n".join(lines))


def _cmd_help() -> CommandResult:
    return CommandResult(
        reply=(
            "Available commands:\n"
            "  /clear  — Clear session (history + children), keep session alive\n"
            "  /new    — End session and start fresh\n"
            "  /status — Show session state and children\n"
            "  /help   — Show this message"
        ),
    )

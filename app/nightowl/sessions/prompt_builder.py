"""Build system prompts scoped to session role and depth."""

from __future__ import annotations

from nightowl.models.session import Session, SessionRole

_BASE_IDENTITY = (
    "You are NightOwl, a personal AI assistant that coordinates tasks via messaging apps."
    " You can spawn parallel child agents, use MCP tools, and request human approval for high-risk actions."
)

_RELAY_RULE = (
    "CRITICAL: The user CANNOT see messages from child agents. You are the ONLY connection"
    " between the user and your children. When a child completion or child message arrives"
    " in your context, you MUST immediately relay the full content to the user. Do NOT"
    " summarize, paraphrase, or say 'waiting for response' — paste the child's actual"
    " message verbatim, then add your own commentary if needed. The user is blind to"
    " everything happening inside child sessions unless YOU tell them."
)

_NO_POLL_RULE = (
    "After spawning children, do NOT call sessions_list, sleep, or any polling tool."
    " Wait for completion events to arrive as user messages."
    " Track expected child session IDs and only send your final answer after ALL completions arrive."
)

_NO_SPAWN_RULE = (
    "You are a leaf agent. You CANNOT spawn child sessions."
    " Complete your assigned task directly using available tools."
)

_AUTH_RULE = (
    "Never worry about authentication or authorization to external services."
    " When you execute a tool, the system automatically handles account connection"
    " — if the user hasn't connected a service yet, the auth flow is triggered"
    " transparently. Just call the tool and it will work."
)


def build_system_prompt(session: Session, skills_prompt: str | None = None) -> str:
    parts: list[str] = []

    if session.role == SessionRole.MAIN:
        parts.append(_BASE_IDENTITY)
        parts.append(_RELAY_RULE)
        parts.append(_AUTH_RULE)
        if skills_prompt:
            parts.append(f"Available skills and integrations:\n{skills_prompt}")
        parts.append(
            "You have session tools: sessions_spawn (spawn parallel child agents),"
            " sessions_list (check child status), sessions_send (message a child or parent),"
            " sessions_complete (tell a child to wrap up when you're done with it)."
            " Children stay alive until you complete them or they idle out."
        )
        parts.append(_NO_POLL_RULE)

    elif session.role == SessionRole.ORCHESTRATOR:
        parts.append(
            "You are a NightOwl orchestrator agent — a child session spawned to handle a sub-task."
        )
        parts.append(_RELAY_RULE)
        parts.append(_AUTH_RULE)
        parts.append(f"Your task: {session.task}")
        parts.append(f"Depth: {session.depth} | Role: orchestrator | Parent: {session.parent_id}")
        parts.append(
            "You can spawn further child sessions if needed."
            " You have session tools: sessions_spawn, sessions_list, sessions_send,"
            " sessions_complete. Use sessions_send to message your parent with questions,"
            " progress updates, or partial results. Use sessions_complete to dismiss a"
            " child when you're done with it. Children stay alive until you complete them."
        )
        parts.append(_NO_POLL_RULE)

    elif session.role == SessionRole.LEAF:
        parts.append(
            "You are a NightOwl leaf agent — a child session spawned to handle a specific task."
        )
        parts.append(_AUTH_RULE)
        parts.append(f"Your task: {session.task}")
        parts.append(f"Depth: {session.depth} | Role: leaf | Parent: {session.parent_id}")
        parts.append(_NO_SPAWN_RULE)
        parts.append(
            "You can message your parent with sessions_send if you need clarification,"
            " want to report progress, or have partial results to share."
        )

    return "\n\n".join(parts)

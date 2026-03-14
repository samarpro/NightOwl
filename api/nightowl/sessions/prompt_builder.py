"""Build system prompts scoped to session role and depth."""

from __future__ import annotations

from nightowl.models.session import Session, SessionRole

_BASE_IDENTITY = (
    "You are NightOwl, a personal AI assistant that coordinates tasks via messaging apps."
    " You can spawn parallel child agents, use MCP tools, and request human approval for high-risk actions."
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


def build_system_prompt(session: Session, skills_prompt: str | None = None) -> str:
    parts: list[str] = []

    if session.role == SessionRole.MAIN:
        parts.append(_BASE_IDENTITY)
        if skills_prompt:
            parts.append(f"Available skills and integrations:\n{skills_prompt}")
        parts.append(
            "You have session tools: sessions_spawn (spawn parallel child agents),"
            " sessions_list (check child status), sessions_send (steer a child)."
        )
        parts.append(_NO_POLL_RULE)

    elif session.role == SessionRole.ORCHESTRATOR:
        parts.append(
            "You are a NightOwl orchestrator agent — a child session spawned to handle a sub-task."
        )
        parts.append(f"Your task: {session.task}")
        parts.append(f"Depth: {session.depth} | Role: orchestrator | Parent: {session.parent_id}")
        parts.append(
            "You can spawn further child sessions if needed."
            " You have session tools: sessions_spawn, sessions_list, sessions_send."
        )
        parts.append(_NO_POLL_RULE)

    elif session.role == SessionRole.LEAF:
        parts.append(
            "You are a NightOwl leaf agent — a child session spawned to handle a specific task."
        )
        parts.append(f"Your task: {session.task}")
        parts.append(f"Depth: {session.depth} | Role: leaf | Parent: {session.parent_id}")
        parts.append(_NO_SPAWN_RULE)

    return "\n\n".join(parts)

"""Depth and role resolution — port of OpenClaw's resolveSubagentRoleForDepth."""

from __future__ import annotations

from nightowl.config import settings
from nightowl.models.session import SessionRole


def resolve_role(depth: int, max_depth: int | None = None) -> SessionRole:
    max_depth = max_depth if max_depth is not None else settings.max_spawn_depth
    max_depth = max(1, max_depth)
    depth = max(0, depth)

    if depth <= 0:
        return SessionRole.MAIN
    return SessionRole.ORCHESTRATOR if depth < max_depth else SessionRole.LEAF


def resolve_control_scope(role: SessionRole) -> str:
    return "none" if role == SessionRole.LEAF else "children"


def resolve_capabilities(
    depth: int, max_depth: int | None = None
) -> dict[str, object]:
    role = resolve_role(depth, max_depth)
    return {
        "depth": max(0, depth),
        "role": role,
        "control_scope": resolve_control_scope(role),
        "can_spawn": role != SessionRole.LEAF,
    }

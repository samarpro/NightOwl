"""Skill tools for agents — tier 2 access to full skill bodies and resources.

Tier 1 (metadata in system prompt) is handled by format_skills_for_prompt().
Tier 2 (on-demand loading) provides load_skill and read_skill_resource as agent tools.
"""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from nightowl.sessions.tools import AgentState

_MAX_SKILLS_PROMPT_CHARS = 30_000


def format_skills_for_prompt(skills: list[dict[str, Any]]) -> str:
    """Format skill metadata into a compact prompt section (tier 1).

    Includes name + description for each enabled skill, within a char budget.
    The agent sees what skills exist and can load details with load_skill.
    """
    if not skills:
        return ""

    lines = ["Available skills (use load_skill to get full instructions):"]
    total = len(lines[0])

    for s in skills:
        line = f"• {s['name']}: {s['description']}"
        if total + len(line) + 1 > _MAX_SKILLS_PROMPT_CHARS:
            lines.append(f"... and {len(skills) - len(lines) + 1} more skills")
            break
        lines.append(line)
        total += len(line) + 1

    return "\n".join(lines)


async def load_skill(ctx: RunContext[AgentState], name: str) -> dict[str, Any] | str:
    """Load the full instructions for a skill by name.

    Use this when you need detailed instructions for how to perform a task
    that matches one of your available skills. Returns the full SKILL.md body.

    Args:
        name: The skill name (e.g. "github", "night-out").
    """
    store = ctx.deps.skill_store
    if store is None:
        return "Skills not configured."
    skill = await store.load_skill(name)
    if skill is None:
        return f"Skill '{name}' not found."
    return {
        "name": skill["name"],
        "description": skill["description"],
        "instructions": skill["body"],
    }


async def read_skill_resource(
    ctx: RunContext[AgentState], skill_name: str, path: str,
) -> str:
    """Read a bundled resource from a skill (script, reference, asset).

    Args:
        skill_name: The skill this resource belongs to.
        path: The resource path within the skill.
    """
    store = ctx.deps.skill_store
    if store is None:
        return "Skills not configured."
    skill = await store.load_skill(skill_name)
    if skill is None:
        return f"Skill '{skill_name}' not found."
    content = await store.load_resource(skill["id"], path)
    if content is None:
        return f"Resource '{path}' not found in skill '{skill_name}'."
    return content

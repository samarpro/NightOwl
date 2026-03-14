"""SKILL.md parser — extracts YAML frontmatter + markdown body from skill files.

Skill format (following OpenClaw convention):
```
---
name: my-skill
description: "What this skill does"
metadata:
  { "openclaw": { ... } }
---

# Skill Name

Markdown body with instructions, examples, etc.
```
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass
class ParsedSkill:
    name: str
    description: str
    body: str
    metadata: dict[str, Any] = field(default_factory=dict)
    user_invocable: bool = False
    homepage: str | None = None
    source: str | None = None


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_skill_md(content: str, source: str | None = None) -> ParsedSkill:
    """Parse a SKILL.md file into structured data.

    Args:
        content: The full SKILL.md text.
        source: Where this skill came from (e.g. "upload", "builtin", file path).

    Returns:
        ParsedSkill with extracted frontmatter and markdown body.

    Raises:
        ValueError: If frontmatter is missing or name is not provided.
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        raise ValueError("SKILL.md must start with YAML frontmatter (--- ... ---)")

    raw_yaml = match.group(1)
    body = content[match.end():].strip()

    try:
        frontmatter = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML frontmatter: {e}") from e

    if not isinstance(frontmatter, dict):
        raise ValueError("Frontmatter must be a YAML mapping")

    name = frontmatter.get("name")
    if not name or not isinstance(name, str):
        raise ValueError("Frontmatter must include a 'name' field")

    name = name.strip().lower()
    if not re.match(r"^[a-z0-9][a-z0-9\-]*$", name):
        raise ValueError(f"Skill name must be lowercase alphanumeric with hyphens: {name!r}")

    description = str(frontmatter.get("description", "")).strip()
    metadata = frontmatter.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    user_invocable = bool(frontmatter.get("user_invocable", False))
    homepage = frontmatter.get("homepage")

    return ParsedSkill(
        name=name,
        description=description,
        body=body,
        metadata=metadata,
        user_invocable=user_invocable,
        homepage=str(homepage) if homepage else None,
        source=source,
    )

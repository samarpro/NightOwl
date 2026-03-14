"""Load built-in skills from the skills_library directory on startup."""

from __future__ import annotations

import logging
from pathlib import Path

from nightowl.skills.parser import parse_skill_md
from nightowl.skills.store import SkillStore

log = logging.getLogger(__name__)

SKILLS_LIBRARY_DIR = Path(__file__).resolve().parent.parent / "skills_library"


async def load_builtin_skills(store: SkillStore) -> int:
    """Scan skills_library/ for SKILL.md files and upsert them into the DB.

    Returns the number of skills loaded.
    """
    if not SKILLS_LIBRARY_DIR.is_dir():
        log.debug("No skills_library directory found at %s", SKILLS_LIBRARY_DIR)
        return 0

    count = 0
    for skill_dir in sorted(SKILLS_LIBRARY_DIR.iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        try:
            content = skill_file.read_text()
            parsed = parse_skill_md(content, source=f"builtin:{skill_dir.name}")
            await store.save_skill(parsed)
            count += 1
        except Exception:
            log.exception("Failed to load builtin skill from %s", skill_file)

    if count:
        log.info("Loaded %d builtin skill(s) from %s", count, SKILLS_LIBRARY_DIR)
    return count

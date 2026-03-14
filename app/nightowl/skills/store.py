"""SkillStore — async data access for skills and skill resources."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nightowl.db import SkillResourceRow, SkillRow
from nightowl.skills.parser import ParsedSkill

log = logging.getLogger(__name__)


class SkillStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def save_skill(self, skill: ParsedSkill) -> int:
        """Upsert a skill by name. Returns the skill ID."""
        async with self._sf() as db:
            stmt = select(SkillRow).where(SkillRow.name == skill.name)
            result = await db.execute(stmt)
            row = result.scalar_one_or_none()

            if row is None:
                row = SkillRow(
                    name=skill.name,
                    description=skill.description,
                    body=skill.body,
                    metadata_json=json.dumps(skill.metadata),
                    user_invocable=skill.user_invocable,
                    homepage=skill.homepage,
                    source=skill.source,
                )
                db.add(row)
            else:
                row.description = skill.description
                row.body = skill.body
                row.metadata_json = json.dumps(skill.metadata)
                row.user_invocable = skill.user_invocable
                row.homepage = skill.homepage
                row.source = skill.source

            await db.commit()
            await db.refresh(row)
            log.info("Saved skill %s (id=%d)", skill.name, row.id)
            return row.id

    async def list_skills(self, enabled_only: bool = True) -> list[dict[str, Any]]:
        """List skills with name, description, and metadata (for prompt tier 1)."""
        async with self._sf() as db:
            stmt = select(SkillRow)
            if enabled_only:
                stmt = stmt.where(SkillRow.enabled == True)  # noqa: E712
            stmt = stmt.order_by(SkillRow.name)
            result = await db.execute(stmt)
            rows = result.scalars().all()

        return [
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "metadata": json.loads(row.metadata_json),
                "user_invocable": row.user_invocable,
                "enabled": row.enabled,
            }
            for row in rows
        ]

    async def load_skill(self, name: str) -> dict[str, Any] | None:
        """Load full skill body (for tier 2 — load_skill tool)."""
        async with self._sf() as db:
            stmt = select(SkillRow).where(SkillRow.name == name)
            result = await db.execute(stmt)
            row = result.scalar_one_or_none()

        if row is None:
            return None

        return {
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "body": row.body,
            "metadata": json.loads(row.metadata_json),
            "user_invocable": row.user_invocable,
            "homepage": row.homepage,
            "source": row.source,
        }

    async def load_resource(self, skill_id: int, path: str) -> str | None:
        """Load a skill resource by skill ID and path."""
        async with self._sf() as db:
            stmt = (
                select(SkillResourceRow)
                .where(SkillResourceRow.skill_id == skill_id)
                .where(SkillResourceRow.path == path)
            )
            result = await db.execute(stmt)
            row = result.scalar_one_or_none()

        return row.content if row else None

    async def save_resource(self, skill_id: int, kind: str, path: str, content: str) -> None:
        """Upsert a skill resource."""
        async with self._sf() as db:
            stmt = (
                select(SkillResourceRow)
                .where(SkillResourceRow.skill_id == skill_id)
                .where(SkillResourceRow.path == path)
            )
            result = await db.execute(stmt)
            row = result.scalar_one_or_none()

            if row is None:
                db.add(SkillResourceRow(
                    skill_id=skill_id, kind=kind, path=path, content=content,
                ))
            else:
                row.kind = kind
                row.content = content
            await db.commit()

    async def delete_skill(self, name: str) -> bool:
        """Delete a skill and its resources. Returns True if found."""
        async with self._sf() as db:
            stmt = select(SkillRow).where(SkillRow.name == name)
            result = await db.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                return False

            await db.execute(
                delete(SkillResourceRow).where(SkillResourceRow.skill_id == row.id)
            )
            await db.delete(row)
            await db.commit()
            log.info("Deleted skill %s", name)
            return True

    async def toggle_skill(self, name: str, enabled: bool) -> bool:
        """Enable or disable a skill. Returns True if found."""
        async with self._sf() as db:
            stmt = select(SkillRow).where(SkillRow.name == name)
            result = await db.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                return False
            row.enabled = enabled
            await db.commit()
            return True

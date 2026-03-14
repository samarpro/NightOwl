"""Session persistence — reads and writes sessions and chat messages to PostgreSQL."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from pydantic import TypeAdapter
from pydantic_ai.messages import ModelMessage
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nightowl.db import ChatMessageRow, SessionRow
from nightowl.models.session import Session, SessionRole, SessionState

log = logging.getLogger(__name__)

_msg_ta = TypeAdapter(ModelMessage)


class SessionStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    async def save_session(self, session: Session) -> None:
        async with self._sf() as db:
            row = await db.get(SessionRow, session.id)
            if row is None:
                row = SessionRow(
                    id=session.id,
                    parent_id=session.parent_id,
                    role=session.role.value,
                    state=session.state.value,
                    depth=session.depth,
                    task=session.task,
                    label=session.label,
                    sandbox_mode=session.sandbox_mode.value if session.sandbox_mode else None,
                )
                db.add(row)
            else:
                row.state = session.state.value
                row.result = session.result
                row.label = session.label
            await db.commit()

    async def update_session_state(
        self, session_id: str, state: SessionState, result: str | None = None,
    ) -> None:
        async with self._sf() as db:
            stmt = (
                update(SessionRow)
                .where(SessionRow.id == session_id)
                .values(state=state.value, result=result)
            )
            await db.execute(stmt)
            await db.commit()

    async def set_channel_route(self, session_id: str, sender_id: str) -> None:
        async with self._sf() as db:
            stmt = (
                update(SessionRow)
                .where(SessionRow.id == session_id)
                .values(channel_route=sender_id)
            )
            await db.execute(stmt)
            await db.commit()

    async def append_messages(
        self, session_id: str, messages: list[Any], start_position: int,
    ) -> None:
        if not messages:
            return
        async with self._sf() as db:
            for i, msg in enumerate(messages):
                kind = getattr(msg, "kind", "unknown")
                content = _msg_ta.dump_json(msg).decode()
                db.add(ChatMessageRow(
                    session_id=session_id,
                    position=start_position + i,
                    kind=kind,
                    content=content,
                ))
            await db.commit()
        log.debug("Persisted %d messages for session %s (pos %d+)", len(messages), session_id, start_position)

    async def load_messages(self, session_id: str) -> list[ModelMessage]:
        async with self._sf() as db:
            stmt = (
                select(ChatMessageRow)
                .where(ChatMessageRow.session_id == session_id)
                .order_by(ChatMessageRow.position)
            )
            result = await db.execute(stmt)
            rows = result.scalars().all()
        messages = []
        for row in rows:
            msg = _msg_ta.validate_json(row.content)
            messages.append(msg)
        log.debug("Loaded %d messages for session %s", len(messages), session_id)
        return messages

    async def load_active_main_session(self) -> tuple[Session, list[ModelMessage]] | None:
        async with self._sf() as db:
            stmt = (
                select(SessionRow)
                .where(SessionRow.role == "main")
                .where(SessionRow.state.in_(["running", "waiting", "pending"]))
                .order_by(SessionRow.created_at.desc())
                .limit(1)
            )
            result = await db.execute(stmt)
            row = result.scalar_one_or_none()
        if row is None:
            return None

        session = Session(
            id=row.id,
            parent_id=row.parent_id,
            role=SessionRole(row.role),
            state=SessionState(row.state),
            depth=row.depth,
            task=row.task,
            label=row.label,
        )
        messages = await self.load_messages(row.id)
        log.info("Resumed session %s with %d messages", row.id, len(messages))
        return session, messages

    async def list_root_sessions(self) -> list[dict[str, Any]]:
        async with self._sf() as db:
            stmt = (
                select(SessionRow)
                .where(SessionRow.parent_id.is_(None))
                .order_by(SessionRow.created_at.desc())
            )
            result = await db.execute(stmt)
            rows = result.scalars().all()
        return [_serialize_session_row(row) for row in rows]

    async def list_child_sessions(self, parent_id: str) -> list[dict[str, Any]]:
        async with self._sf() as db:
            stmt = (
                select(SessionRow)
                .where(SessionRow.parent_id == parent_id)
                .order_by(SessionRow.created_at.desc())
            )
            result = await db.execute(stmt)
            rows = result.scalars().all()
        return [_serialize_session_row(row) for row in rows]

    async def fail_orphaned_children(self) -> int:
        async with self._sf() as db:
            stmt = (
                update(SessionRow)
                .where(SessionRow.role != "main")
                .where(SessionRow.state.in_(["pending", "running", "waiting"]))
                .values(state="failed", result="Orphaned — server restarted")
            )
            result = await db.execute(stmt)
            await db.commit()
            count = result.rowcount
        if count:
            log.info("Failed %d orphaned child sessions", count)
        return count


def _serialize_session_row(row: SessionRow) -> dict[str, Any]:
    return serialize_session(session=row)


def serialize_session(session: Session | SessionRow | dict[str, Any]) -> dict[str, Any]:
    if isinstance(session, dict):
        return {
            "id": session.get("id"),
            "parentId": session.get("parent_id"),
            "role": _enum_value(session.get("role")),
            "state": _enum_value(session.get("state")),
            "depth": session.get("depth", 0),
            "task": session.get("task"),
            "label": session.get("label"),
            "sandboxMode": _enum_value(session.get("sandbox_mode")),
            "channelRoute": session.get("channel_route"),
            "createdAt": _isoformat(session.get("created_at")),
            "completedAt": _isoformat(session.get("completed_at")),
            "result": session.get("result"),
        }

    return {
        "id": session.id,
        "parentId": session.parent_id,
        "role": _enum_value(session.role),
        "state": _enum_value(session.state),
        "depth": session.depth,
        "task": session.task,
        "label": session.label,
        "sandboxMode": _enum_value(getattr(session, "sandbox_mode", None)),
        "channelRoute": getattr(session, "channel_route", None),
        "createdAt": _isoformat(getattr(session, "created_at", None)),
        "completedAt": _isoformat(getattr(session, "completed_at", None)),
        "result": getattr(session, "result", None),
    }


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value

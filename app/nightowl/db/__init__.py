"""Database engine, session factory, and model re-exports.

Usage:
    from nightowl.db import init_db, close_db, get_session_factory
    from nightowl.db import SessionRow, ChatMessageRow, ...  # model re-exports
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from nightowl.config import settings
from nightowl.db.models import (
    ApprovalRow,
    Base,
    ChatMessageRow,
    MessageRow,
    SessionRow,
    SkillResourceRow,
    SkillRow,
)

__all__ = [
    "init_db",
    "close_db",
    "get_session_factory",
    "Base",
    "ApprovalRow",
    "ChatMessageRow",
    "MessageRow",
    "SessionRow",
    "SkillResourceRow",
    "SkillRow",
]

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> async_sessionmaker[AsyncSession]:
    """Create the async engine and session factory.

    Schema is managed by Alembic migrations — run `pdm run migrate` to apply.
    """
    global _engine, _session_factory
    _engine = create_async_engine(settings.database_url, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_factory


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database not initialised — call init_db() first")
    return _session_factory


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None

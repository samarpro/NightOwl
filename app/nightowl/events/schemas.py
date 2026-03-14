"""Typed runtime event contracts for websocket delivery."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class RuntimeEvent(BaseModel):
    event_id: str
    event_type: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    session_id: str | None = None
    channel: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

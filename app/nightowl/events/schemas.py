"""Typed runtime event contracts for websocket delivery."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RuntimeEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_id: str = Field(serialization_alias="eventId")
    event_type: str = Field(serialization_alias="eventType")
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), serialization_alias="occurredAt"
    )
    session_id: str | None = Field(default=None, serialization_alias="sessionId")
    channel: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

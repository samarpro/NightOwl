"""Message data models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Message(BaseModel):
    id: int | None = None
    session_id: str
    role: str
    content: str


class ChannelMessage(BaseModel):
    channel: str
    sender_id: str
    text: str
    thread_id: str | None = None
    chat_id: str | None = None
    message_id: str | None = None
    sender_display_name: str | None = None
    received_at: datetime | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

"""Message data models."""

from __future__ import annotations

from pydantic import BaseModel


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

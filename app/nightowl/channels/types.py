"""Normalized channel routing and delivery types."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class ChannelSessionKey(BaseModel):
    channel: str
    sender_id: str
    thread_id: str | None = None
    chat_id: str | None = None


class ChannelTarget(BaseModel):
    channel: str
    chat_id: str
    sender_id: str | None = None
    thread_id: str | None = None
    message_id: str | None = None


class DeliveryResult(BaseModel):
    delivered: bool
    provider_message_id: str | None = None
    error: str | None = None


class ChannelOutbound(Protocol):
    async def send_text(self, target: ChannelTarget, text: str) -> DeliveryResult: ...

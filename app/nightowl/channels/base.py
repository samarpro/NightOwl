"""ChannelBridge ABC and ChannelRegistry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from nightowl.models.approval import ApprovalRequest
from nightowl.models.message import ChannelMessage


class ChannelBridge(ABC):
    """Abstract base class for messaging channel bridges."""

    channel_id: str

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def send_message(self, user_id: str, text: str) -> None: ...

    @abstractmethod
    async def send_approval_request(self, user_id: str, approval: ApprovalRequest) -> None: ...

    @abstractmethod
    def normalize_inbound(self, raw: dict[str, Any]) -> ChannelMessage: ...


class ChannelRegistry:
    """Registry of channel bridges with last-channel-per-user tracking."""

    def __init__(self) -> None:
        self._bridges: dict[str, ChannelBridge] = {}
        self._last_channel: dict[str, dict[str, str]] = {}

    def register(self, bridge: ChannelBridge) -> None:
        self._bridges[bridge.channel_id] = bridge

    def get(self, channel_id: str) -> ChannelBridge | None:
        return self._bridges.get(channel_id)

    def list_channels(self) -> list[str]:
        return list(self._bridges.keys())

    def set_last_channel(self, user_id: str, *, channel: str, chat_id: str) -> None:
        self._last_channel[user_id] = {"channel": channel, "chat_id": chat_id}

    def get_last_channel(self, user_id: str) -> dict[str, str] | None:
        return self._last_channel.get(user_id)

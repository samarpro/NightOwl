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
    """Registry of channel bridges with last-channel-per-user and session routing."""

    def __init__(self) -> None:
        self._bridges: dict[str, ChannelBridge] = {}
        self._last_channel: dict[str, dict[str, str]] = {}
        self._session_channels: dict[str, dict[str, str]] = {}

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

    # ── Session → channel routing ─────────────────────────────────

    def set_session_channel(self, session_id: str, channel_id: str, chat_id: str) -> None:
        """Map a session to the channel + chat_id it should reply to."""
        self._session_channels[session_id] = {"channel": channel_id, "chat_id": chat_id}

    def get_session_channel(self, session_id: str) -> dict[str, str] | None:
        return self._session_channels.get(session_id)

    async def send_session_reply(self, session_id: str, text: str) -> None:
        """Send a text reply via the bridge associated with a session."""
        info = self._session_channels.get(session_id)
        if info is None:
            return
        bridge = self._bridges.get(info["channel"])
        if bridge is None:
            return
        await bridge.send_message(info["chat_id"], text)

    def clear_session(self, session_id: str) -> None:
        self._session_channels.pop(session_id, None)

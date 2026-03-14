"""Channel outbound adapter registry."""

from __future__ import annotations

from nightowl.channels.types import ChannelOutbound


class ChannelRegistry:
    def __init__(self) -> None:
        self._outbound: dict[str, ChannelOutbound] = {}

    def register_outbound(self, channel: str, adapter: ChannelOutbound) -> None:
        self._outbound[channel] = adapter

    def get_outbound(self, channel: str) -> ChannelOutbound | None:
        return self._outbound.get(channel)

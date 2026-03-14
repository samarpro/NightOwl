"""In-memory route and reply-target store for channel-backed sessions."""

from __future__ import annotations

from nightowl.channels.types import ChannelSessionKey, ChannelTarget


def _route_id(key: ChannelSessionKey) -> str:
    return "|".join(
        [
            key.channel,
            key.chat_id or "",
            key.thread_id or "",
            key.sender_id,
        ]
    )


class ChannelSessionRouter:
    def __init__(self) -> None:
        self._routes: dict[str, str] = {}
        self._session_routes: dict[str, set[str]] = {}
        self._targets: dict[str, ChannelTarget] = {}

    def bind(
        self,
        key: ChannelSessionKey,
        session_id: str,
        target: ChannelTarget,
    ) -> None:
        route = _route_id(key)
        self._routes[route] = session_id
        self._session_routes.setdefault(session_id, set()).add(route)
        self._targets[session_id] = target

    def resolve(self, key: ChannelSessionKey) -> str | None:
        return self._routes.get(_route_id(key))

    def remember_target(self, session_id: str, target: ChannelTarget) -> None:
        self._targets[session_id] = target

    def get_target(self, session_id: str) -> ChannelTarget | None:
        return self._targets.get(session_id)

    def clear_session(self, session_id: str) -> None:
        for route in self._session_routes.pop(session_id, set()):
            self._routes.pop(route, None)
        self._targets.pop(session_id, None)

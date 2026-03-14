"""Token store — append-only capture of agent activity per session.

Every model request, response, tool call, and tool result is recorded as a
token entry. The intent classifier consumes these to build intent nodes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TokenType(StrEnum):
    THINKING = "thinking"       # model request (prompt sent to LLM)
    RESPONSE = "response"       # model text response
    TOOL_CALL = "tool_call"     # tool invocation
    TOOL_RESULT = "tool_result" # tool return value
    SPAWN = "spawn"             # child session spawned
    COMPLETION = "completion"   # child completion received


@dataclass
class TokenEntry:
    session_id: str
    token_type: TokenType
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class TokenStore:
    """In-memory append-only token store, keyed by session_id."""

    def __init__(self) -> None:
        self._entries: dict[str, list[TokenEntry]] = {}

    def append(self, entry: TokenEntry) -> int:
        """Append a token entry. Returns the index within the session."""
        entries = self._entries.setdefault(entry.session_id, [])
        entries.append(entry)
        return len(entries) - 1

    def get_session(self, session_id: str) -> list[TokenEntry]:
        return self._entries.get(session_id, [])

    def get_range(self, session_id: str, start: int, end: int | None = None) -> list[TokenEntry]:
        entries = self._entries.get(session_id, [])
        return entries[start:end]

    def get_latest(self, session_id: str, n: int = 10) -> list[TokenEntry]:
        entries = self._entries.get(session_id, [])
        return entries[-n:]

    def clear_session(self, session_id: str) -> None:
        self._entries.pop(session_id, None)

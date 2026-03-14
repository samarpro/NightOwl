"""Shared ingress service for normalized channel messages."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from nightowl.channels.base import ChannelRegistry
from nightowl.models.message import ChannelMessage
from nightowl.models.session import Session, SessionState
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.runner import SessionRuntime, create_session_runtime, process_runtime_message

log = logging.getLogger(__name__)


class IngestResult(BaseModel):
    session_id: str
    created: bool


@dataclass
class _WorkerState:
    runtime: SessionRuntime
    task: asyncio.Task[None]


class IngressService:
    def __init__(
        self,
        manager: SessionManager,
        registry: ChannelRegistry,
        runtime_factory: Callable[[Session, SessionManager], SessionRuntime] = create_session_runtime,
        process_turn: Callable[
            [SessionRuntime, str, Callable[[dict[str, Any]], Awaitable[None]]],
            Awaitable[str],
        ] = process_runtime_message,
    ) -> None:
        self._manager = manager
        self._registry = registry
        self._runtime_factory = runtime_factory
        self._process_turn = process_turn
        self._workers: dict[str, _WorkerState] = {}
        self._routes: dict[str, str] = {}  # route_key -> session_id

    def _route_key(self, message: ChannelMessage) -> str:
        return f"{message.channel}:{message.sender_id}"

    async def ingest(self, message: ChannelMessage) -> IngestResult:
        session, created = await self._resolve_session(message)
        chat_id = message.sender_id
        self._registry.set_session_channel(session.id, message.channel, chat_id)
        self._registry.set_last_channel(message.sender_id, channel=message.channel, chat_id=chat_id)

        if self._manager.hitl_gate is not None:
            self._manager.hitl_gate.set_last_channel(session.id, message.channel, chat_id)

        await self._manager._emit({
            "type": "channel:message_received",
            "session_id": session.id,
            "channel": message.channel,
            "sender_id": message.sender_id,
            "text": message.text,
        })

        self._ensure_worker(session)
        await self._manager.send_to_session(session.id, message.text)
        return IngestResult(session_id=session.id, created=created)

    async def shutdown(self) -> None:
        for state in self._workers.values():
            state.task.cancel()
        if self._workers:
            await asyncio.gather(
                *(state.task for state in self._workers.values()),
                return_exceptions=True,
            )
        self._workers.clear()

    async def _resolve_session(self, message: ChannelMessage) -> tuple[Session, bool]:
        key = self._route_key(message)
        session_id = self._routes.get(key)
        if session_id:
            session = self._manager.get_session(session_id)
            if session and session.state not in {SessionState.COMPLETED, SessionState.FAILED}:
                await self._manager._emit({
                    "type": "session:resumed",
                    "session_id": session.id,
                    "channel": message.channel,
                    "reason": "inbound_channel_message",
                })
                return session, False
            if session:
                self._registry.clear_session(session.id)

        session = await self._manager.create_main_session(message.text, channel=message.channel)
        self._routes[key] = session.id
        return session, True

    def _ensure_worker(self, session: Session) -> None:
        current = self._workers.get(session.id)
        if current and not current.task.done():
            return

        runtime = self._runtime_factory(session, self._manager)
        task = asyncio.create_task(self._session_worker(session, runtime), name=f"ingress:{session.id}")
        self._workers[session.id] = _WorkerState(runtime=runtime, task=task)

    async def _session_worker(self, session: Session, runtime: SessionRuntime) -> None:
        queue = self._manager.get_queue(session.id)
        if queue is None:
            return

        while True:
            message = await queue.get()
            try:
                output = await self._process_turn(runtime, message, self._manager._emit)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.exception("Session worker %s failed", session.id)
                await self._manager._emit({
                    "type": "error",
                    "session_id": session.id,
                    "message": str(exc),
                })
                continue

            if not output.strip():
                continue

            channel_info = self._registry.get_session_channel(session.id)
            await self._manager._emit({
                "type": "agent:response",
                "session_id": session.id,
                "channel": channel_info["channel"] if channel_info else None,
                "text": output,
            })
            await self._registry.send_session_reply(session.id, output)

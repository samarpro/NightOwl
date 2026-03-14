"""Shared ingress service for normalized channel messages."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from nightowl.channels.base import ChannelRegistry
from nightowl.ingest.commands import handle_command
from nightowl.models.message import ChannelMessage
from nightowl.models.session import Session, SessionState
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.runner import SessionRuntime, create_session_runtime, process_runtime_message
from nightowl.skills.tools import format_skills_for_prompt

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
        runtime_factory: Callable[..., SessionRuntime] = create_session_runtime,
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
        self._main_session_id: str | None = None
        self._restored_history: list[Any] | None = None

    def set_resumed_session(self, session_id: str, message_history: list[Any]) -> None:
        """Called on startup when a session is resumed from DB."""
        self._main_session_id = session_id
        self._restored_history = message_history

    async def ingest(self, message: ChannelMessage) -> IngestResult:
        session, created = await self._resolve_session(message)
        chat_id = message.sender_id
        self._registry.set_session_channel(session.id, message.channel, chat_id)
        self._registry.set_last_channel(message.sender_id, channel=message.channel, chat_id=chat_id)

        if self._manager.hitl_gate is not None:
            self._manager.hitl_gate.set_last_channel(session.id, message.channel, chat_id)

        # Persist channel route
        if self._manager.store:
            await self._manager.store.set_channel_route(session.id, message.sender_id)

        await self._manager._emit({
            "type": "channel:message_received",
            "session_id": session.id,
            "channel": message.channel,
            "sender_id": message.sender_id,
            "text": message.text,
        })

        inbound_text = message.text
        if self._manager.hitl_gate is not None:
            if self._manager.hitl_gate.handle_text_response(message.text):
                return IngestResult(session_id=session.id, created=created)
            redirected = self._manager.hitl_gate.consume_redirect_instruction(session.id, message.text)
            if redirected is not None:
                inbound_text = redirected

        # Slash commands — intercept before reaching the agent
        cmd_result = await handle_command(
            inbound_text, session.id, self._manager, self._workers,
        )
        if cmd_result is not None:
            if cmd_result.reply:
                await self._registry.send_session_reply(session.id, cmd_result.reply)
                await self._manager._emit({
                    "type": "agent:response",
                    "session_id": session.id,
                    "channel": message.channel,
                    "text": cmd_result.reply,
                })
            if cmd_result.end_session:
                self._main_session_id = None
                self._restored_history = None
            return IngestResult(session_id=session.id, created=created)

        await self._ensure_worker(session)
        await self._manager.send_to_session(session.id, inbound_text)
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
        # Check in-memory main session first
        if self._main_session_id:
            session = self._manager.get_session(self._main_session_id)
            if session and session.state not in {SessionState.COMPLETED, SessionState.FAILED}:
                return session, False
            # Session ended — clear it
            self._main_session_id = None
            self._restored_history = None

        # Try DB resume (first message after restart)
        if self._manager.store:
            result = await self._manager.load_and_resume()
            if result:
                session, messages = result
                self._main_session_id = session.id
                self._restored_history = messages
                log.info("Resumed session %s from DB with %d messages", session.id, len(messages))
                return session, False

        # Create fresh session
        session = await self._manager.create_main_session(message.text, channel=message.channel)
        self._main_session_id = session.id
        self._restored_history = None
        return session, True

    async def _ensure_worker(self, session: Session) -> None:
        current = self._workers.get(session.id)
        if current and not current.task.done():
            return

        # If we have restored history from DB, pass it to the runtime
        history = self._restored_history
        self._restored_history = None  # consumed

        # Load tier 1 skill metadata for the system prompt
        skills_prompt = None
        skill_store = getattr(self._manager, "skill_store", None)
        if skill_store:
            skills = await skill_store.list_skills()
            skills_prompt = format_skills_for_prompt(skills) or None

        runtime = self._runtime_factory(
            session, self._manager, message_history=history, skills_prompt=skills_prompt,
        )
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

            # Trigger intent classification in background
            intent_graph = getattr(self._manager, "intent_graph", None)
            if intent_graph:
                intent_graph.schedule_processing(session.id)

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

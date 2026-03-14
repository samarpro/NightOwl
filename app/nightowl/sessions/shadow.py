"""Shadow agent — toolless clone for user Q&A without polluting the live agent.

The shadow agent has the same model, system prompt, and message history as the
live agent, but no tools. The user chats with it via the dashboard to ask
questions about what the agent is doing. If a correction is needed, the shadow
pushes a steering message to the live session's queue.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from pydantic_ai import Agent

from nightowl.config import settings
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.prompt_builder import build_system_prompt
from nightowl.sessions.runner import _build_agent, _iter_agent, _noop_event
from nightowl.sessions.tools import AgentState

log = logging.getLogger(__name__)

_SHADOW_PROMPT_SUFFIX = (
    "\n\nYou are in SHADOW MODE. You are answering questions about the work"
    " this session is doing. You have the full conversation history but NO tools."
    " You cannot take actions — only explain, analyse, and suggest corrections."
    " If you believe the agent needs to change course, clearly state the"
    " correction and the user can relay it to the live agent."
)


class ShadowRuntime:
    def __init__(
        self,
        shadow_id: str,
        live_session_id: str,
        agent: Agent[AgentState, str],
        deps: AgentState,
        message_history: list[Any],
    ) -> None:
        self.shadow_id = shadow_id
        self.live_session_id = live_session_id
        self.agent = agent
        self.deps = deps
        self.message_history = list(message_history)  # snapshot copy


class ShadowManager:
    def __init__(self, manager: SessionManager) -> None:
        self._manager = manager
        self._shadows: dict[str, ShadowRuntime] = {}

    async def create(self, session_id: str) -> str:
        """Create a shadow agent for a live session. Returns shadow_id."""
        session = self._manager.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        # Load message history — try in-memory first (from ingest worker), then DB
        message_history: list[Any] = []
        store = self._manager.store
        if store:
            message_history = await store.load_messages(session_id)

        # Build toolless agent with enriched prompt
        system_prompt = build_system_prompt(session) + _SHADOW_PROMPT_SUFFIX
        agent = _build_agent(session, system_prompt, include_tools=False)
        deps = AgentState(session_id=session_id, manager=self._manager)

        shadow_id = f"shadow:{uuid.uuid4().hex[:12]}"
        self._shadows[shadow_id] = ShadowRuntime(
            shadow_id=shadow_id,
            live_session_id=session_id,
            agent=agent,
            deps=deps,
            message_history=message_history,
        )
        log.info("Created shadow %s for session %s (%d messages)", shadow_id, session_id, len(message_history))
        return shadow_id

    async def message(self, shadow_id: str, text: str) -> str:
        """Send a message to a shadow agent. Returns the response."""
        shadow = self._shadows.get(shadow_id)
        if shadow is None:
            raise ValueError(f"Shadow {shadow_id} not found")

        output, shadow.message_history = await _iter_agent(
            shadow.agent, text, shadow.deps, shadow.message_history, _noop_event,
        )
        return output

    async def correct(self, shadow_id: str, text: str) -> None:
        """Push a correction from the shadow to the live agent's queue."""
        shadow = self._shadows.get(shadow_id)
        if shadow is None:
            raise ValueError(f"Shadow {shadow_id} not found")

        correction = (
            f"[SYSTEM: CORRECTION FROM USER VIA SHADOW AGENT]\n"
            f"The user reviewed your work and wants you to adjust:\n"
            f"---\n{text}\n---"
        )
        await self._manager.send_to_session(shadow.live_session_id, correction)
        log.info("Sent correction from shadow %s to session %s", shadow_id, shadow.live_session_id)

    def destroy(self, shadow_id: str) -> None:
        self._shadows.pop(shadow_id, None)

    def get(self, shadow_id: str) -> ShadowRuntime | None:
        return self._shadows.get(shadow_id)

"""Session runner — executes a Pydantic AI agent session with the spawn/wait loop."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import logfire
from pydantic_ai import Agent
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.providers.bedrock import BedrockProvider

from nightowl.config import settings

logfire.configure(token=settings.logfire_token or None)
logfire.instrument_pydantic_ai()
from nightowl.models.session import Session, SessionRole, SessionState
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.prompt_builder import build_system_prompt
from nightowl.composio_tools.meta_tools import composio_execute, composio_search_tools
from nightowl.sessions.tools import AgentState, sessions_list, sessions_send, sessions_spawn

log = logging.getLogger(__name__)


def _build_agent(session: Session, system_prompt: str) -> Agent[AgentState, str]:
    model_name = session.model_override or settings.bedrock_model
    provider = BedrockProvider(
        region_name=settings.bedrock_region,
        api_key=settings.bedrock_api_key or None,
    )
    model = BedrockConverseModel(model_name=model_name, provider=provider)
    agent: Agent[AgentState, str] = Agent(
        model=model,
        system_prompt=system_prompt,
        deps_type=AgentState,
        retries=2,
    )

    # Register session tools (leaf agents cannot spawn)
    if session.role != SessionRole.LEAF:
        agent.tool(sessions_spawn)
        agent.tool(sessions_list)
    agent.tool(sessions_send)

    # Composio tools — available to all roles
    agent.tool(composio_search_tools)
    agent.tool(composio_execute)

    return agent


async def run_child_session(session: Session, manager: SessionManager) -> None:
    """Entry point for background child sessions. Uses the session's task as the initial message."""
    await run_session(session, manager, session.task)


async def run_session(
    session: Session,
    manager: SessionManager,
    initial_message: str,
    skills_prompt: str | None = None,
) -> str:
    system_prompt = build_system_prompt(session, skills_prompt=skills_prompt)
    agent = _build_agent(session, system_prompt)
    deps = AgentState(session_id=session.id, manager=manager)

    session.state = SessionState.RUNNING
    await manager._emit({"type": "session:running", "session_id": session.id})

    # Initial agent run
    result = await agent.run(initial_message, deps=deps)
    response = result.output

    # If children were spawned, enter wait loop
    queue = manager.get_queue(session.id)
    if queue and not manager.all_completions_received(session.id):
        session.state = SessionState.WAITING
        await manager._emit({"type": "session:waiting", "session_id": session.id})

        while not manager.all_completions_received(session.id):
            try:
                message = await asyncio.wait_for(queue.get(), timeout=300)
            except asyncio.TimeoutError:
                log.warning("Session %s timed out waiting for children", session.id)
                break

            # Re-run agent with the completion message
            result = await agent.run(
                message,
                deps=deps,
                message_history=result.new_messages(),
            )
            response = result.output

    # Session done
    await manager.complete_session(session.id, response)
    return response

"""Session runner — executes a Pydantic AI agent session with the spawn/wait loop."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import logfire
import stamina
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
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


def _is_transient(exc: Exception) -> bool:
    """Return True for errors worth retrying (rate limits, server errors)."""
    if isinstance(exc, ModelHTTPError):
        return exc.status_code in (429, 500, 502, 503, 504)
    return False


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


@stamina.retry(on=_is_transient, attempts=5, wait_initial=1.0, wait_max=30.0, wait_jitter=2.0)
async def _agent_run(
    agent: Agent[AgentState, str],
    prompt: str,
    deps: AgentState,
    message_history: list[Any] | None = None,
) -> Any:
    """Run an agent with exponential backoff on transient errors."""
    kwargs: dict[str, Any] = {"deps": deps}
    if message_history is not None:
        kwargs["message_history"] = message_history
    return await agent.run(prompt, **kwargs)


async def run_child_session(session: Session, manager: SessionManager) -> None:
    """Entry point for background child sessions. Uses the session's task as the initial message."""
    await run_session(session, manager, session.task)


async def run_interactive(
    manager: SessionManager,
    get_input: Any,
    put_output: Any,
) -> None:
    """Multi-turn interactive loop. Non-blocking on child sessions.

    Args:
        manager: SessionManager (must already have child_runner and broadcast set).
        get_input: async callable() -> str | None. Returns user input, or None to quit.
        put_output: async callable(str) -> None. Sends agent output to the user.
    """
    session = await manager.create_main_session("interactive")
    system_prompt = build_system_prompt(session)
    agent = _build_agent(session, system_prompt)
    deps = AgentState(session_id=session.id, manager=manager)
    session.state = SessionState.RUNNING
    message_history: list[Any] = []

    while True:
        # Drain pending child completions
        queue = manager.get_queue(session.id)
        while queue and not queue.empty():
            message = queue.get_nowait()
            result = await _agent_run(agent, message, deps, message_history)
            message_history = result.new_messages()
            await put_output(result.output)

        user_input = await get_input()
        if user_input is None:
            break
        if not user_input.strip():
            continue

        # Drain again — completions may have arrived during input wait
        while queue and not queue.empty():
            message = queue.get_nowait()
            result = await _agent_run(agent, message, deps, message_history)
            message_history = result.new_messages()
            await put_output(result.output)

        result = await _agent_run(agent, user_input, deps, message_history)
        message_history = result.new_messages()
        await put_output(result.output)


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
    result = await _agent_run(agent, initial_message, deps)
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
            result = await _agent_run(agent, message, deps, result.new_messages())
            response = result.output

    # Session done
    await manager.complete_session(session.id, response)
    return response

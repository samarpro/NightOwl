"""Session runner — executes Pydantic AI agents via iter() for full streaming visibility."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

import logfire
import stamina
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.providers.bedrock import BedrockProvider
from pydantic_graph import End

from nightowl.config import settings

logfire.configure(token=settings.logfire_token or None)
logfire.instrument_pydantic_ai()

from nightowl.composio_tools.meta_tools import composio_execute, composio_search_tools
from nightowl.models.session import Session, SessionRole, SessionState
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.prompt_builder import build_system_prompt
from nightowl.sessions.tools import AgentState, sessions_list, sessions_send, sessions_spawn

log = logging.getLogger(__name__)

# Type alias for the event callback the caller provides
EventCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class SessionRuntime:
    def __init__(
        self,
        agent: Agent[AgentState, str],
        deps: AgentState,
        message_history: list[Any] | None = None,
    ) -> None:
        self.agent = agent
        self.deps = deps
        self.message_history = message_history or []


def _is_transient(exc: Exception) -> bool:
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

    if session.role != SessionRole.LEAF:
        agent.tool(sessions_spawn)
        agent.tool(sessions_list)
    agent.tool(sessions_send)
    agent.tool(composio_search_tools)
    agent.tool(composio_execute)

    return agent


async def _noop_event(_: dict[str, Any]) -> None:
    pass


@stamina.retry(on=_is_transient, attempts=5, wait_initial=1.0, wait_max=30.0, wait_jitter=2.0)
async def _iter_agent(
    agent: Agent[AgentState, str],
    prompt: str,
    deps: AgentState,
    message_history: list[Any] | None,
    on_event: EventCallback,
    interrupt: asyncio.Event | None = None,
) -> tuple[str, list[Any]]:
    """Run an agent via iter(), emitting node events. Supports interruption between nodes.

    Returns (output, new_message_history).
    """
    kwargs: dict[str, Any] = {"deps": deps}
    if message_history is not None:
        kwargs["message_history"] = message_history

    async with agent.iter(prompt, **kwargs) as agent_run:
        async for node in agent_run:
            if Agent.is_model_request_node(node):
                await on_event({"type": "node:model_request", "session_id": deps.session_id})
            elif Agent.is_call_tools_node(node):
                tool_parts = [
                    p for p in node.model_response.parts
                    if hasattr(p, "tool_name")
                ]
                await on_event({
                    "type": "node:tool_call",
                    "session_id": deps.session_id,
                    "tools": [p.tool_name for p in tool_parts],
                })
            elif Agent.is_end_node(node):
                await on_event({"type": "node:end", "session_id": deps.session_id})

            # Check for interrupt between nodes
            if interrupt and interrupt.is_set():
                log.info("Session %s interrupted between nodes", deps.session_id)
                break

    output = agent_run.result.output if agent_run.result else ""
    history = agent_run.result.all_messages() if agent_run.result else (message_history or [])
    return output, history


# ── Public API ────────────────────────────────────────────────────


async def process_message(
    session_id: str,
    message: str,
    manager: SessionManager,
    agent: Agent[AgentState, str],
    deps: AgentState,
    message_history: list[Any],
    on_event: EventCallback = _noop_event,
    interrupt: asyncio.Event | None = None,
) -> tuple[str, list[Any]]:
    """Process a single message in a session. Core function for all entrypoints.

    1. Drains pending child completions from the queue
    2. Feeds them + the new message to the agent via iter()
    3. Returns (output, updated_message_history)
    """
    # Drain pending child completions first — agent needs context
    queue = manager.get_queue(session_id)
    while queue and not queue.empty():
        completion = queue.get_nowait()
        await on_event({"type": "child_completion", "session_id": session_id})
        _, message_history = await _iter_agent(
            agent, completion, deps, message_history, on_event,
        )

    # Process the actual message
    output, message_history = await _iter_agent(
        agent, message, deps, message_history, on_event, interrupt,
    )
    return output, message_history


def create_session_runtime(session: Session, manager: SessionManager) -> SessionRuntime:
    system_prompt = build_system_prompt(session)
    agent = _build_agent(session, system_prompt)
    deps = AgentState(session_id=session.id, manager=manager, hitl_gate=manager.hitl_gate)
    return SessionRuntime(agent=agent, deps=deps)


async def process_runtime_message(
    runtime: SessionRuntime,
    message: str,
    on_event: EventCallback = _noop_event,
    interrupt: asyncio.Event | None = None,
) -> str:
    output, runtime.message_history = await _iter_agent(
        runtime.agent,
        message,
        runtime.deps,
        runtime.message_history,
        on_event,
        interrupt,
    )
    return output


async def run_child_session(session: Session, manager: SessionManager) -> None:
    """Entry point for background child sessions."""
    system_prompt = build_system_prompt(session)
    agent = _build_agent(session, system_prompt)
    deps = AgentState(session_id=session.id, manager=manager, hitl_gate=manager.hitl_gate)
    session.state = SessionState.RUNNING
    await manager._emit({"type": "session:running", "session_id": session.id})

    output, _ = await _iter_agent(agent, session.task, deps, None, manager._emit)

    # If children were spawned, wait for them
    queue = manager.get_queue(session.id)
    if queue and not manager.all_completions_received(session.id):
        session.state = SessionState.WAITING
        await manager._emit({"type": "session:waiting", "session_id": session.id})
        history: list[Any] = []

        while not manager.all_completions_received(session.id):
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=300)
            except asyncio.TimeoutError:
                log.warning("Child session %s timed out waiting for sub-children", session.id)
                break
            output, history = await _iter_agent(agent, msg, deps, history, manager._emit)

    await manager.complete_session(session.id, output)


async def run_interactive(
    manager: SessionManager,
    get_input: Callable[[], Coroutine[Any, Any, str | None]],
    put_output: Callable[[str], Coroutine[Any, Any, None]],
    on_event: EventCallback = _noop_event,
) -> None:
    """Multi-turn interactive loop. Thin wrapper around process_message."""
    session = await manager.create_main_session("interactive")
    system_prompt = build_system_prompt(session)
    agent = _build_agent(session, system_prompt)
    deps = AgentState(session_id=session.id, manager=manager, hitl_gate=manager.hitl_gate)
    session.state = SessionState.RUNNING
    message_history: list[Any] = []

    while True:
        user_input = await get_input()
        if user_input is None:
            break
        if not user_input.strip():
            continue

        try:
            output, message_history = await process_message(
                session.id, user_input, manager, agent, deps, message_history,
                on_event=on_event,
            )
        except Exception as e:
            await put_output(f"[error] {e}")
            continue

        await put_output(output)

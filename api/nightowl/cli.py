"""Slim CLI chat for iterative testing — bypasses HTTP, talks directly to the engine."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.providers.bedrock import BedrockProvider

from nightowl.composio_tools.meta_tools import composio_execute, composio_search_tools
from nightowl.config import settings
from nightowl.hitl.gate import HITLGate
from nightowl.models.session import Session, SessionRole, SessionState
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.prompt_builder import build_system_prompt
from nightowl.sessions.runner import run_child_session
from nightowl.sessions.tools import AgentState, sessions_list, sessions_send, sessions_spawn

log = logging.getLogger(__name__)


def _build_cli_agent(session: Session, system_prompt: str) -> Agent[AgentState, str]:
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


async def _drain_completions(
    agent: Agent[AgentState, str],
    deps: AgentState,
    session: Session,
    manager: SessionManager,
    message_history: list[Any],
) -> tuple[str, list[Any]]:
    """Wait for child completions and re-run agent with each one."""
    queue = manager.get_queue(session.id)
    response = ""

    while not manager.all_completions_received(session.id):
        try:
            message = await asyncio.wait_for(queue.get(), timeout=300)
        except asyncio.TimeoutError:
            log.warning("Session %s timed out waiting for children", session.id)
            break

        result = await agent.run(message, deps=deps, message_history=message_history)
        response = result.output
        message_history = result.new_messages()

    return response, message_history


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    manager = SessionManager()
    manager.set_child_runner(run_child_session)

    broadcast: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    manager.set_broadcast_queue(broadcast)

    # HITL gate for CLI — approvals go to stdout
    gate = HITLGate(manager=manager, broadcast_queue=broadcast)

    session = await manager.create_main_session("cli-chat")
    system_prompt = build_system_prompt(session)
    agent = _build_cli_agent(session, system_prompt)
    deps = AgentState(session_id=session.id, manager=manager)

    session.state = SessionState.RUNNING
    message_history: list[Any] = []

    print("NightOwl CLI — one session, persistent context. Ctrl+C to quit.\n")
    print(f"[session {session.id}]\n")

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue

        try:
            result = await agent.run(
                user_input, deps=deps, message_history=message_history,
            )
            response = result.output
            message_history = result.new_messages()

            # If children were spawned, drain completions
            if not manager.all_completions_received(session.id):
                session.state = SessionState.WAITING
                print("[waiting for child agents...]\n")
                response, message_history = await _drain_completions(
                    agent, deps, session, manager, message_history,
                )
                session.state = SessionState.RUNNING

        except Exception as e:
            print(f"[error] {e}\n")
            continue

        print(f"nightowl> {response}\n")


if __name__ == "__main__":
    asyncio.run(main())

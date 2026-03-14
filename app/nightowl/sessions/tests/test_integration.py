"""Integration tests — actually invoke Bedrock. Require BEDROCK_API_KEY to be set."""

from __future__ import annotations

import pytest

from nightowl.config import settings
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.runner import create_session_runtime, process_runtime_message

needs_bedrock = pytest.mark.skipif(
    not settings.bedrock_api_key,
    reason="BEDROCK_API_KEY not set",
)


@needs_bedrock
class TestBedrockInvocation:
    async def test_agent_responds_to_simple_message(self):
        manager = SessionManager()
        session = await manager.create_main_session("Say hello")
        runtime = create_session_runtime(session, manager)
        response = await process_runtime_message(runtime, "Say hello in one sentence.")
        assert len(response) > 0

    async def test_agent_response_is_coherent(self):
        manager = SessionManager()
        session = await manager.create_main_session("What is 2+2?")
        runtime = create_session_runtime(session, manager)
        response = await process_runtime_message(runtime, "What is 2+2? Reply with just the number.")
        assert "4" in response

    async def test_agent_has_session_tools_available(self):
        manager = SessionManager()
        session = await manager.create_main_session("List your tools")
        runtime = create_session_runtime(session, manager)
        response = await process_runtime_message(
            runtime,
            "What session tools do you have? List their names briefly.",
        )
        assert "sessions_spawn" in response.lower() or "spawn" in response.lower()

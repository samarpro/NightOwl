"""Integration tests — actually invoke Bedrock. Require BEDROCK_API_KEY to be set.

These test through the SessionManager boundary, not through runner internals.
If the runner is refactored, these should still pass.
"""

from __future__ import annotations

import asyncio

import pytest

from nightowl.config import settings
from nightowl.models.session import SpawnRequest
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.runner import create_session_runtime, process_runtime_message, run_child_session

needs_bedrock = pytest.mark.skipif(
    not settings.bedrock_api_key,
    reason="BEDROCK_API_KEY not set",
)


@needs_bedrock
class TestBedrockEndToEnd:
    async def test_child_delivers_to_parent(self):
        """Spawn a child as a background task, verify the parent receives output."""
        manager = SessionManager()
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(
            parent.id, SpawnRequest(task="Say hello in one sentence."),
        )

        # Run child in background (it stays alive now)
        task = asyncio.create_task(run_child_session(child, manager))
        try:
            q = manager.get_queue(parent.id)
            msg = await asyncio.wait_for(q.get(), timeout=30)
            assert isinstance(msg, str)
            assert len(msg) > 0
        finally:
            # Complete the child so it exits
            await manager.complete_session(child.id, "test done")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def test_child_response_is_coherent(self):
        """Ask a factual question, verify the answer is in the result."""
        manager = SessionManager()
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(
            parent.id,
            SpawnRequest(task="What is 2+2? Reply with just the number."),
        )

        task = asyncio.create_task(run_child_session(child, manager))
        try:
            q = manager.get_queue(parent.id)
            msg = await asyncio.wait_for(q.get(), timeout=30)
            assert "4" in msg
        finally:
            await manager.complete_session(child.id, "test done")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


@needs_bedrock
class TestSessionRuntime:
    async def test_runtime_responds_to_message(self):
        manager = SessionManager()
        session = await manager.create_main_session("Say hello")
        runtime = create_session_runtime(session, manager)
        response = await process_runtime_message(runtime, "Say hello in one sentence.")
        assert len(response) > 0

    async def test_runtime_response_is_coherent(self):
        manager = SessionManager()
        session = await manager.create_main_session("What is 2+2?")
        runtime = create_session_runtime(session, manager)
        response = await process_runtime_message(runtime, "What is 2+2? Reply with just the number.")
        assert "4" in response

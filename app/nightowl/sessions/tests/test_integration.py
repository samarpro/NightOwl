"""Integration tests — actually invoke Bedrock. Require BEDROCK_API_KEY to be set.

These test through the SessionManager boundary, not through runner internals.
If the runner is refactored, these should still pass.
"""

from __future__ import annotations

import asyncio

import pytest

from nightowl.config import settings
from nightowl.models.session import SessionState, SpawnRequest
from nightowl.sessions.manager import SessionManager

needs_bedrock = pytest.mark.skipif(
    not settings.bedrock_api_key,
    reason="BEDROCK_API_KEY not set",
)


def _get_runner():
    """Import the child-session runner by whatever name it currently has."""
    # Isolates us from function renames inside runner.py.
    from nightowl.sessions import runner

    for name in ("run_child_session", "run_session"):
        fn = getattr(runner, name, None)
        if fn is not None:
            return fn
    raise ImportError("No child-session runner found in nightowl.sessions.runner")


@needs_bedrock
class TestBedrockEndToEnd:
    async def test_child_completes_and_delivers_to_parent(self):
        """Spawn a child, let Bedrock answer, verify the parent receives the result."""
        manager = SessionManager()
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(
            parent.id, SpawnRequest(task="Say hello in one sentence."),
        )

        run = _get_runner()
        await run(child, manager)

        # Child should be completed
        assert child.state == SessionState.COMPLETED
        # Parent's queue should have the completion message
        q = manager.get_queue(parent.id)
        msg = await asyncio.wait_for(q.get(), timeout=5)
        assert isinstance(msg, str)
        assert len(msg) > 0

    async def test_child_response_is_coherent(self):
        """Ask a factual question, verify the answer is in the result."""
        manager = SessionManager()
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(
            parent.id,
            SpawnRequest(task="What is 2+2? Reply with just the number."),
        )

        run = _get_runner()
        await run(child, manager)

        # The completion delivered to parent should contain "4"
        q = manager.get_queue(parent.id)
        msg = await asyncio.wait_for(q.get(), timeout=5)
        assert "4" in msg

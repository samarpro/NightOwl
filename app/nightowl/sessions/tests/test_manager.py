"""Tests for SessionManager — behaviour-driven, not implementation-coupled."""

from __future__ import annotations

import asyncio

import pytest

from nightowl.models.session import SandboxMode, SessionRole, SessionState, SpawnRequest
from nightowl.sessions.manager import SessionManager


class TestCreateMainSession:
    async def test_creates_session_with_task(self, manager: SessionManager):
        session = await manager.create_main_session("Plan a night out")
        assert session.task == "Plan a night out"
        assert session.role == SessionRole.MAIN
        assert session.state == SessionState.RUNNING
        assert session.depth == 0

    async def test_session_is_retrievable(self, manager: SessionManager):
        session = await manager.create_main_session("Do something")
        found = manager.get_session(session.id)
        assert found is not None
        assert found.id == session.id

    async def test_each_session_gets_unique_id(self, manager: SessionManager):
        s1 = await manager.create_main_session("task 1")
        s2 = await manager.create_main_session("task 2")
        assert s1.id != s2.id

    async def test_session_gets_inbound_queue(self, manager: SessionManager):
        session = await manager.create_main_session("task")
        assert manager.get_queue(session.id) is not None


class TestSpawnChild:
    async def test_spawns_child_with_correct_depth(self, manager: SessionManager):
        parent = await manager.create_main_session("parent task")
        child = await manager.spawn_child(parent.id, SpawnRequest(task="child task"))
        assert child.depth == 1
        assert child.parent_id == parent.id

    async def test_child_role_follows_depth_resolution(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(parent.id, SpawnRequest(task="child"))
        # depth 1 with default max_spawn_depth=3 → orchestrator
        assert child.role == SessionRole.ORCHESTRATOR

    async def test_child_registered_on_parent(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(parent.id, SpawnRequest(task="child"))
        assert child.id in parent.children
        assert child.id in parent.expected_completions

    async def test_child_appears_in_list_children(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        c1 = await manager.spawn_child(parent.id, SpawnRequest(task="a"))
        c2 = await manager.spawn_child(parent.id, SpawnRequest(task="b"))
        children = manager.list_children(parent.id)
        child_ids = {c.id for c in children}
        assert c1.id in child_ids
        assert c2.id in child_ids

    async def test_child_label_preserved(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(
            parent.id, SpawnRequest(task="search restaurants", label="restaurant-search")
        )
        assert child.label == "restaurant-search"


class TestDepthLimitEnforcement:
    async def test_rejects_spawn_beyond_max_depth(self, manager: SessionManager):
        # Build a chain to max depth (default 3)
        parent = await manager.create_main_session("root")
        d1 = await manager.spawn_child(parent.id, SpawnRequest(task="d1"))
        d2 = await manager.spawn_child(d1.id, SpawnRequest(task="d2"))
        d3 = await manager.spawn_child(d2.id, SpawnRequest(task="d3"))
        # d3 is at depth 3 (max), trying to spawn from it should fail
        with pytest.raises(ValueError, match="depth"):
            await manager.spawn_child(d3.id, SpawnRequest(task="d4"))


class TestMaxChildrenEnforcement:
    async def test_rejects_spawn_beyond_max_children(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        for i in range(5):  # default max is 5
            await manager.spawn_child(parent.id, SpawnRequest(task=f"child-{i}"))
        with pytest.raises(ValueError, match="children"):
            await manager.spawn_child(parent.id, SpawnRequest(task="one-too-many"))


class TestIdleTimeout:
    async def test_child_gets_default_idle_timeout(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(parent.id, SpawnRequest(task="child"))
        assert child.idle_timeout == 30

    async def test_parent_can_set_child_idle_timeout(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(
            parent.id, SpawnRequest(task="long task", idle_timeout=300)
        )
        assert child.idle_timeout == 300


class TestSandboxInheritance:
    async def test_sandboxed_parent_forces_sandboxed_child(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        parent.sandbox_mode = SandboxMode.BROWSER
        child = await manager.spawn_child(
            parent.id, SpawnRequest(task="child", sandbox=SandboxMode.NONE)
        )
        assert child.sandbox_mode == SandboxMode.BROWSER

    async def test_unsandboxed_parent_allows_unsandboxed_child(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(
            parent.id, SpawnRequest(task="child", sandbox=SandboxMode.NONE)
        )
        assert child.sandbox_mode == SandboxMode.NONE

    async def test_unsandboxed_parent_allows_sandboxed_child(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(
            parent.id, SpawnRequest(task="child", sandbox=SandboxMode.CLI)
        )
        assert child.sandbox_mode == SandboxMode.CLI


class TestCompletionDelivery:
    async def test_completing_child_delivers_message_to_parent_queue(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(parent.id, SpawnRequest(task="fetch data"))
        await manager.complete_session(child.id, "here is the data")

        q = manager.get_queue(parent.id)
        msg = await asyncio.wait_for(q.get(), timeout=1)
        assert "here is the data" in msg

    async def test_completion_message_tagged_as_child_output(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(parent.id, SpawnRequest(task="fetch"))
        await manager.complete_session(child.id, "result")

        q = manager.get_queue(parent.id)
        msg = await asyncio.wait_for(q.get(), timeout=1)
        assert "child" in msg.lower()
        assert "cannot see this" in msg.lower()

    async def test_completion_includes_child_label(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(
            parent.id, SpawnRequest(task="search", label="restaurant-finder")
        )
        await manager.complete_session(child.id, "found 5 restaurants")

        q = manager.get_queue(parent.id)
        msg = await asyncio.wait_for(q.get(), timeout=1)
        assert "restaurant-finder" in msg

    async def test_completed_child_removed_from_expected(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(parent.id, SpawnRequest(task="work"))
        assert not manager.all_completions_received(parent.id)

        await manager.complete_session(child.id, "done")
        assert manager.all_completions_received(parent.id)

    async def test_failed_child_still_delivers_to_parent(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        child = await manager.spawn_child(parent.id, SpawnRequest(task="risky"))
        await manager.complete_session(child.id, "something went wrong", success=False)

        q = manager.get_queue(parent.id)
        msg = await asyncio.wait_for(q.get(), timeout=1)
        assert "failed" in msg.lower()

    async def test_multiple_children_all_must_complete(self, manager: SessionManager):
        parent = await manager.create_main_session("parent")
        c1 = await manager.spawn_child(parent.id, SpawnRequest(task="a"))
        c2 = await manager.spawn_child(parent.id, SpawnRequest(task="b"))

        await manager.complete_session(c1.id, "done a")
        assert not manager.all_completions_received(parent.id)

        await manager.complete_session(c2.id, "done b")
        assert manager.all_completions_received(parent.id)


class TestSendToSession:
    async def test_message_arrives_on_session_queue(self, manager: SessionManager):
        session = await manager.create_main_session("task")
        await manager.send_to_session(session.id, "steering message")

        q = manager.get_queue(session.id)
        msg = await asyncio.wait_for(q.get(), timeout=1)
        assert msg == "steering message"

    async def test_send_to_nonexistent_session_does_not_raise(self, manager: SessionManager):
        # Should log warning but not crash
        await manager.send_to_session("nonexistent", "hello")


class TestBroadcastEvents:
    async def test_session_creation_emits_event(self, manager_with_broadcast):
        manager, bus = manager_with_broadcast
        await manager.create_main_session("task")
        event = bus.get_nowait()
        assert event is not None
        assert event["type"] == "session:created"

    async def test_spawn_emits_event(self, manager_with_broadcast):
        manager, bus = manager_with_broadcast
        parent = await manager.create_main_session("parent")
        bus.get_nowait()  # consume create event
        await manager.spawn_child(parent.id, SpawnRequest(task="child"))
        event = bus.get_nowait()
        assert event is not None
        assert event["type"] == "session:spawned"
        assert event["parent"] == parent.id

    async def test_completion_emits_event(self, manager_with_broadcast):
        manager, bus = manager_with_broadcast
        session = await manager.create_main_session("task")
        bus.get_nowait()  # consume create event
        await manager.complete_session(session.id, "done")
        event = bus.get_nowait()
        assert event is not None
        assert event["type"] == "session:completed"


class TestCleanup:
    async def test_cleanup_removes_session_and_queue(self, manager: SessionManager):
        session = await manager.create_main_session("task")
        await manager.cleanup_session(session.id)
        assert manager.get_session(session.id) is None
        assert manager.get_queue(session.id) is None

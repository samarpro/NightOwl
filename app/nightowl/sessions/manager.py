"""SessionManager — core orchestrator for agent session lifecycles."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from nightowl.config import settings
from nightowl.models.session import (
    SandboxMode,
    Session,
    SessionRole,
    SessionState,
    SpawnRequest,
    TaskCompletionEvent,
)
from nightowl.sessions.depth import resolve_role

log = logging.getLogger(__name__)


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._queues: dict[str, asyncio.Queue[Any]] = {}
        self._event_bus: Any | None = None  # EventBus instance
        self._child_runner: Any | None = None  # async callable(Session, SessionManager)
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self.hitl_gate: Any | None = None  # HITLGate instance, shared across all sessions
        self.channel_registry: Any | None = None  # ChannelRegistry instance
        self.store: Any | None = None  # SessionStore instance

    def set_child_runner(self, runner: Any) -> None:
        """Set the coroutine used to execute child sessions in the background."""
        self._child_runner = runner

    def set_event_bus(self, bus: Any) -> None:
        """Set the Redis event bus for publishing events."""
        self._event_bus = bus

    async def _emit(self, event: dict[str, Any]) -> None:
        if self._event_bus is not None:
            await self._event_bus.publish(event)

    # ── Session creation ──────────────────────────────────────────

    async def create_main_session(self, task: str, channel: str | None = None) -> Session:
        session_id = f"session:{uuid.uuid4().hex[:12]}"
        session = Session(
            id=session_id,
            role=SessionRole.MAIN,
            state=SessionState.RUNNING,
            depth=0,
            task=task,
        )
        self._sessions[session_id] = session
        self._queues[session_id] = asyncio.Queue()
        await self._emit({"type": "session:created", "session": session.model_dump(), "channel": channel})
        if self.store:
            await self.store.save_session(session)
        return session

    async def spawn_child(
        self, parent_id: str, request: SpawnRequest
    ) -> Session:
        parent = self._sessions.get(parent_id)
        if parent is None:
            raise ValueError(f"Parent session {parent_id} not found")

        child_depth = parent.depth + 1
        if child_depth > settings.max_spawn_depth:
            raise ValueError(
                f"Max spawn depth ({settings.max_spawn_depth}) exceeded"
            )
        if len(parent.children) >= settings.max_children_per_session:
            raise ValueError(
                f"Max children per session ({settings.max_children_per_session}) exceeded"
            )

        # Sandbox inheritance: sandboxed parent -> sandboxed children
        sandbox = request.sandbox
        if parent.sandbox_mode and parent.sandbox_mode != SandboxMode.NONE:
            if sandbox is None or sandbox == SandboxMode.NONE:
                sandbox = parent.sandbox_mode

        child_role = resolve_role(child_depth)
        session_id = f"session:{uuid.uuid4().hex[:12]}"
        child = Session(
            id=session_id,
            parent_id=parent_id,
            role=child_role,
            state=SessionState.PENDING,
            depth=child_depth,
            task=request.task,
            label=request.label,
            sandbox_mode=sandbox,
            model_override=request.model,
        )
        self._sessions[session_id] = child
        self._queues[session_id] = asyncio.Queue()
        parent.children.append(session_id)
        parent.expected_completions.add(session_id)

        await self._emit(
            {"type": "session:spawned", "parent": parent_id, "child": child.model_dump()}
        )
        if self.store:
            await self.store.save_session(child)
        log.info("Spawned child %s (depth=%d, role=%s) from %s", session_id, child_depth, child_role, parent_id)

        # Kick off the child session as a background task
        if self._child_runner is not None:
            task = asyncio.create_task(
                self._run_child_safe(child), name=f"child:{session_id}",
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        return child

    async def _run_child_safe(self, child: Session) -> None:
        """Run a child session, catching errors and completing as failed."""
        try:
            await self._child_runner(child, self)
        except Exception:
            log.exception("Child session %s failed", child.id)
            await self.complete_session(child.id, "Child session crashed", success=False)

    # ── Session lifecycle ─────────────────────────────────────────

    async def complete_session(self, session_id: str, result: str, success: bool = True) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        session.state = SessionState.COMPLETED if success else SessionState.FAILED
        session.result = result

        # Clean up sandbox container if one was created for this session
        sandbox_mgr = getattr(self, "sandbox_manager", None)
        if sandbox_mgr is not None:
            container_id = sandbox_mgr.get_container_for_session(session_id)
            if container_id is not None:
                await sandbox_mgr.cleanup(container_id)
                log.info("Cleaned up sandbox container %s for session %s", container_id, session_id)

        await self._emit(
            {
                "type": "session:completed",
                "session_id": session_id,
                "success": success,
                "session": session.model_dump(),
                "result": result,
            }
        )
        if self.store:
            await self.store.update_session_state(session_id, session.state, result)

        if session.parent_id:
            # Free the child slot on the parent so new children can be spawned
            parent = self._sessions.get(session.parent_id)
            if parent:
                try:
                    parent.children.remove(session_id)
                except ValueError:
                    pass
            await self.deliver_completion_to_parent(
                TaskCompletionEvent(
                    child_session_id=session_id,
                    parent_session_id=session.parent_id,
                    result=result,
                    success=success,
                )
            )

    async def deliver_completion_to_parent(self, event: TaskCompletionEvent) -> None:
        parent = self._sessions.get(event.parent_session_id)
        if parent is None:
            log.warning("Parent %s not found for completion from %s", event.parent_session_id, event.child_session_id)
            return

        parent.expected_completions.discard(event.child_session_id)
        child = self._sessions.get(event.child_session_id)
        label = child.label or event.child_session_id if child else event.child_session_id

        message = (
            f"[SYSTEM: CHILD SESSION COMPLETED — {label}]\n"
            f"Status: {'success' if event.success else 'failed'}\n"
            f"The following is output from child agent {label}. "
            f"The user CANNOT see this — you MUST relay relevant content to the user.\n"
            f"---\n{event.result}\n---"
        )
        await self.send_to_session(event.parent_session_id, message)

    async def send_to_session(self, session_id: str, message: str) -> None:
        q = self._queues.get(session_id)
        if q is None:
            log.warning("No queue for session %s", session_id)
            return
        await q.put(message)

    # ── Query ─────────────────────────────────────────────────────

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def get_queue(self, session_id: str) -> asyncio.Queue[Any] | None:
        return self._queues.get(session_id)

    def list_sessions(self) -> list[Session]:
        return list(self._sessions.values())

    def list_children(self, parent_id: str) -> list[Session]:
        parent = self._sessions.get(parent_id)
        if parent is None:
            return []
        return [self._sessions[cid] for cid in parent.children if cid in self._sessions]

    def all_completions_received(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return True
        return len(session.expected_completions) == 0

    async def cleanup_session(self, session_id: str) -> None:
        sandbox_mgr = getattr(self, "sandbox_manager", None)
        if sandbox_mgr is not None:
            container_id = sandbox_mgr.get_container_for_session(session_id)
            if container_id is not None:
                await sandbox_mgr.cleanup(container_id)
        self._sessions.pop(session_id, None)
        self._queues.pop(session_id, None)

    # ── Persistence ───────────────────────────────────────────────

    async def load_and_resume(self) -> tuple[Any, list[Any]] | None:
        """Load the active main session from DB on startup.

        Returns (Session, message_history) or None.
        """
        if self.store is None:
            return None
        result = self.store.load_active_main_session()
        if asyncio.iscoroutine(result):
            result = await result
        if result is None:
            return None
        session, messages = result
        self._sessions[session.id] = session
        self._queues[session.id] = asyncio.Queue()
        await self.store.fail_orphaned_children()
        log.info("Resumed session %s (%d messages)", session.id, len(messages))
        return session, messages

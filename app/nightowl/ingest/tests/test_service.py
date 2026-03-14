from __future__ import annotations

import asyncio
from typing import Any

from nightowl.channels.base import ChannelBridge, ChannelRegistry
from nightowl.models.approval import ApprovalDecision, ApprovalRequest
from nightowl.models.message import ChannelMessage
from nightowl.sessions.manager import SessionManager
from nightowl.sessions.tests.conftest import FakeEventBus
from nightowl.ingest.service import IngressService


class _FakeRuntime:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id


async def _fake_process(runtime: _FakeRuntime, message: str, on_event):
    await on_event({"type": "agent:response", "session_id": runtime.session_id, "text": f"echo:{message}"})
    return f"echo:{message}"


def _fake_runtime_factory(session, manager, message_history=None, skills_prompt=None):
    return _FakeRuntime(session.id)


class FakeBridge(ChannelBridge):
    channel_id = "telegram"

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str | None]] = []

    async def start(self) -> None:
        pass

    async def send_message(
        self,
        user_id: str,
        text: str,
        *,
        reply_to_message_id: str | None = None,
    ) -> None:
        self.sent.append((user_id, text, reply_to_message_id))

    async def send_approval_request(self, user_id: str, approval: ApprovalRequest) -> dict[str, str] | None:
        return {"message_id": "42"}

    def normalize_inbound(self, raw: dict[str, Any]) -> ChannelMessage:
        return ChannelMessage(channel=self.channel_id, sender_id=raw["from"], text=raw["text"])


class TestIngressService:
    async def test_creates_session_for_new_route(self):
        manager = SessionManager()
        bus = FakeEventBus()
        manager.set_event_bus(bus)
        registry = ChannelRegistry()
        bridge = FakeBridge()
        registry.register(bridge)
        service = IngressService(
            manager=manager,
            registry=registry,
            runtime_factory=_fake_runtime_factory,
            process_turn=_fake_process,
        )

        result = await service.ingest(ChannelMessage(
            channel="telegram",
            sender_id="u1",
            text="hello",
        ))
        await asyncio.sleep(0)

        assert result.created is True
        assert manager.get_session(result.session_id) is not None
        assert bridge.sent == [("u1", "echo:hello", None)]
        await service.shutdown()

    async def test_resumes_existing_session_for_same_route(self):
        manager = SessionManager()
        bus = FakeEventBus()
        manager.set_event_bus(bus)
        registry = ChannelRegistry()
        bridge = FakeBridge()
        registry.register(bridge)
        service = IngressService(
            manager=manager,
            registry=registry,
            runtime_factory=_fake_runtime_factory,
            process_turn=_fake_process,
        )
        message = ChannelMessage(channel="telegram", sender_id="u1", text="hello")
        first = await service.ingest(message)
        second = await service.ingest(message.model_copy(update={"text": "again"}))
        await asyncio.sleep(0)

        assert first.session_id == second.session_id
        assert second.created is False
        await service.shutdown()

    async def test_redirect_follow_up_replaces_next_message_with_redirect_instruction(self):
        manager = SessionManager()
        bus = FakeEventBus()
        manager.set_event_bus(bus)
        registry = ChannelRegistry()
        bridge = FakeBridge()
        registry.register(bridge)
        service = IngressService(
            manager=manager,
            registry=registry,
            runtime_factory=_fake_runtime_factory,
            process_turn=_fake_process,
        )

        first = await service.ingest(ChannelMessage(channel="telegram", sender_id="u1", text="hello"))
        session = manager.get_session(first.session_id)
        assert session is not None
        gate = manager.hitl_gate
        if gate is None:
            from nightowl.hitl.gate import HITLGate
            gate = HITLGate(manager=manager, event_bus=bus, registry=registry)
            manager.hitl_gate = gate
            gate.set_last_channel(session.id, "telegram", "u1")

        gate._pending_redirects[session.id] = {  # type: ignore[attr-defined]
            "approval_id": "approval:test",
            "tool_name": "GMAIL_SEND",
            "reply_to_message_id": "42",
        }

        await service.ingest(ChannelMessage(channel="telegram", sender_id="u1", text="Send it tomorrow instead"))
        await asyncio.sleep(0)

        assert any("USER REDIRECTED A BLOCKED ACTION" in text for _, text, _ in bridge.sent)
        await service.shutdown()

from __future__ import annotations

import asyncio

from nightowl.channels.outbound import ChannelDeliveryService
from nightowl.channels.registry import ChannelRegistry
from nightowl.channels.session_routing import ChannelSessionRouter
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


def _fake_runtime_factory(session, manager):
    return _FakeRuntime(session.id)


class _FakeOutbound:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_text(self, target, text):
        self.sent.append((target.chat_id, text))
        from nightowl.channels.types import DeliveryResult

        return DeliveryResult(delivered=True, provider_message_id="provider:1")


class TestIngressService:
    async def test_creates_session_for_new_route(self):
        manager = SessionManager()
        bus = FakeEventBus()
        manager.set_event_bus(bus)
        routing = ChannelSessionRouter()
        registry = ChannelRegistry()
        outbound = _FakeOutbound()
        registry.register_outbound("telegram", outbound)
        delivery = ChannelDeliveryService(routing, registry, manager._emit)
        service = IngressService(
            manager=manager,
            routing=routing,
            delivery=delivery,
            runtime_factory=_fake_runtime_factory,
            process_turn=_fake_process,
        )

        result = await service.ingest(ChannelMessage(
            channel="telegram",
            sender_id="u1",
            chat_id="c1",
            text="hello",
        ))
        await asyncio.sleep(0)

        assert result.created is True
        assert manager.get_session(result.session_id) is not None
        assert outbound.sent == [("c1", "echo:hello")]
        await service.shutdown()

    async def test_resumes_existing_session_for_same_route(self):
        manager = SessionManager()
        bus = FakeEventBus()
        manager.set_event_bus(bus)
        routing = ChannelSessionRouter()
        registry = ChannelRegistry()
        outbound = _FakeOutbound()
        registry.register_outbound("telegram", outbound)
        delivery = ChannelDeliveryService(routing, registry, manager._emit)
        service = IngressService(
            manager=manager,
            routing=routing,
            delivery=delivery,
            runtime_factory=_fake_runtime_factory,
            process_turn=_fake_process,
        )
        message = ChannelMessage(channel="telegram", sender_id="u1", chat_id="c1", text="hello")
        first = await service.ingest(message)
        second = await service.ingest(message.model_copy(update={"text": "again"}))
        await asyncio.sleep(0)

        assert first.session_id == second.session_id
        event_types = [event["type"] for event in bus.drain()]
        assert "session:resumed" in event_types
        await service.shutdown()

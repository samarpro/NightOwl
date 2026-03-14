"""Tests for ChannelBridge ABC and channel registry.

Module under test: nightowl/channels/base.py

ChannelBridge is the abstract base class all channel bridges implement.
The channel registry tracks registered bridges and last-channel-per-user.

These tests verify the contract that any concrete bridge must satisfy,
and that the registry correctly routes messages to the right bridge.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from nightowl.models.message import ChannelMessage
from nightowl.models.approval import ApprovalRequest, RiskLevel
from nightowl.channels.base import ChannelBridge, ChannelRegistry


# ---------------------------------------------------------------------------
# Concrete test double — minimal valid implementation of the ABC
# ---------------------------------------------------------------------------


class StubBridge(ChannelBridge):
    """Minimal concrete bridge for testing the ABC contract."""

    channel_id = "stub"

    def __init__(self) -> None:
        self.started = False
        self.sent_messages: list[tuple[str, str]] = []
        self.sent_approvals: list[tuple[str, ApprovalRequest]] = []

    async def start(self) -> None:
        self.started = True

    async def send_message(self, user_id: str, text: str) -> None:
        self.sent_messages.append((user_id, text))

    async def send_approval_request(self, user_id: str, approval: ApprovalRequest) -> None:
        self.sent_approvals.append((user_id, approval))

    def normalize_inbound(self, raw: dict[str, Any]) -> ChannelMessage:
        return ChannelMessage(
            channel=self.channel_id,
            sender_id=raw["from"],
            text=raw["text"],
            thread_id=raw.get("thread"),
        )


# ---------------------------------------------------------------------------
# ABC contract enforcement
# ---------------------------------------------------------------------------


class TestChannelBridgeABC:
    def test_cannot_instantiate_abc_directly(self):
        with pytest.raises(TypeError):
            ChannelBridge()

    def test_concrete_subclass_instantiates(self):
        bridge = StubBridge()
        assert bridge.channel_id == "stub"

    def test_subclass_missing_send_message_raises(self):
        """A bridge that doesn't implement send_message cannot be instantiated."""
        with pytest.raises(TypeError):
            class BadBridge(ChannelBridge):
                channel_id = "bad"
                async def start(self) -> None: ...
                async def send_approval_request(self, user_id, approval): ...
                def normalize_inbound(self, raw): ...
            BadBridge()

    def test_subclass_missing_normalize_raises(self):
        with pytest.raises(TypeError):
            class BadBridge(ChannelBridge):
                channel_id = "bad"
                async def start(self) -> None: ...
                async def send_message(self, user_id, text): ...
                async def send_approval_request(self, user_id, approval): ...
            BadBridge()


# ---------------------------------------------------------------------------
# StubBridge behaviour (validates the contract works end-to-end)
# ---------------------------------------------------------------------------


class TestBridgeSendMessage:
    async def test_send_message_records_user_and_text(self):
        bridge = StubBridge()
        await bridge.send_message("user123", "Hello from NightOwl")
        assert bridge.sent_messages == [("user123", "Hello from NightOwl")]

    async def test_send_multiple_messages(self):
        bridge = StubBridge()
        await bridge.send_message("u1", "first")
        await bridge.send_message("u2", "second")
        assert len(bridge.sent_messages) == 2


class TestBridgeSendApproval:
    async def test_send_approval_request(self):
        bridge = StubBridge()
        approval = ApprovalRequest(
            id="approval:abc",
            session_id="session:x",
            tool_name="GMAIL_SEND",
            tool_args={"to": "alice@example.com"},
            risk_level=RiskLevel.HIGH,
        )
        await bridge.send_approval_request("user123", approval)
        assert len(bridge.sent_approvals) == 1
        assert bridge.sent_approvals[0][0] == "user123"
        assert bridge.sent_approvals[0][1].id == "approval:abc"


class TestNormalizeInbound:
    def test_normalizes_raw_dict_to_channel_message(self):
        bridge = StubBridge()
        msg = bridge.normalize_inbound({"from": "user456", "text": "Plan a night out"})
        assert isinstance(msg, ChannelMessage)
        assert msg.channel == "stub"
        assert msg.sender_id == "user456"
        assert msg.text == "Plan a night out"

    def test_normalizes_with_thread_id(self):
        bridge = StubBridge()
        msg = bridge.normalize_inbound({"from": "u1", "text": "hi", "thread": "t99"})
        assert msg.thread_id == "t99"

    def test_normalizes_without_thread_id(self):
        bridge = StubBridge()
        msg = bridge.normalize_inbound({"from": "u1", "text": "hi"})
        assert msg.thread_id is None


class TestBridgeStart:
    async def test_start_can_be_awaited(self):
        bridge = StubBridge()
        await bridge.start()
        assert bridge.started is True


# ---------------------------------------------------------------------------
# Channel registry
# ---------------------------------------------------------------------------


class TestChannelRegistry:
    def test_register_and_retrieve_bridge(self):
        registry = ChannelRegistry()
        bridge = StubBridge()
        registry.register(bridge)
        assert registry.get("stub") is bridge

    def test_get_unregistered_channel_returns_none(self):
        registry = ChannelRegistry()
        assert registry.get("nonexistent") is None

    def test_register_multiple_bridges(self):
        registry = ChannelRegistry()

        class TelegramStub(StubBridge):
            channel_id = "telegram"

        class WhatsAppStub(StubBridge):
            channel_id = "whatsapp"

        tg = TelegramStub()
        wa = WhatsAppStub()
        registry.register(tg)
        registry.register(wa)
        assert registry.get("telegram") is tg
        assert registry.get("whatsapp") is wa

    def test_list_registered_channels(self):
        registry = ChannelRegistry()
        registry.register(StubBridge())
        channels = registry.list_channels()
        assert "stub" in channels

    def test_duplicate_register_replaces(self):
        """Re-registering the same channel_id replaces the old bridge."""
        registry = ChannelRegistry()
        bridge1 = StubBridge()
        bridge2 = StubBridge()
        registry.register(bridge1)
        registry.register(bridge2)
        assert registry.get("stub") is bridge2


# ---------------------------------------------------------------------------
# Last-channel tracking
# ---------------------------------------------------------------------------


class TestLastChannelTracking:
    def test_set_and_get_last_channel(self):
        registry = ChannelRegistry()
        registry.set_last_channel("user123", channel="telegram", chat_id="99887766")
        last = registry.get_last_channel("user123")
        assert last is not None
        assert last["channel"] == "telegram"
        assert last["chat_id"] == "99887766"

    def test_get_last_channel_unknown_user_returns_none(self):
        registry = ChannelRegistry()
        assert registry.get_last_channel("unknown_user") is None

    def test_last_channel_updates_on_new_message(self):
        """When a user messages from a different channel, last_channel should update."""
        registry = ChannelRegistry()
        registry.set_last_channel("user123", channel="telegram", chat_id="111")
        registry.set_last_channel("user123", channel="whatsapp", chat_id="222")
        last = registry.get_last_channel("user123")
        assert last["channel"] == "whatsapp"
        assert last["chat_id"] == "222"

    def test_last_channel_per_user_isolation(self):
        registry = ChannelRegistry()
        registry.set_last_channel("alice", channel="telegram", chat_id="111")
        registry.set_last_channel("bob", channel="whatsapp", chat_id="222")
        assert registry.get_last_channel("alice")["channel"] == "telegram"
        assert registry.get_last_channel("bob")["channel"] == "whatsapp"


# ---------------------------------------------------------------------------
# Registry + bridge integration
# ---------------------------------------------------------------------------


class TestRegistrySendViaLastChannel:
    async def test_send_to_user_via_last_channel(self):
        """Registry should be able to route a message to the user's last channel."""
        registry = ChannelRegistry()
        bridge = StubBridge()
        registry.register(bridge)
        registry.set_last_channel("user123", channel="stub", chat_id="user123")

        last = registry.get_last_channel("user123")
        channel_bridge = registry.get(last["channel"])
        await channel_bridge.send_message(last["chat_id"], "Your reservation is confirmed")

        assert bridge.sent_messages == [("user123", "Your reservation is confirmed")]

    async def test_send_approval_via_last_channel(self):
        registry = ChannelRegistry()
        bridge = StubBridge()
        registry.register(bridge)
        registry.set_last_channel("user123", channel="stub", chat_id="user123")

        approval = ApprovalRequest(
            id="approval:xyz",
            session_id="session:1",
            tool_name="STRIPE_CHARGE",
            tool_args={"amount": 50},
            risk_level=RiskLevel.CRITICAL,
        )
        last = registry.get_last_channel("user123")
        channel_bridge = registry.get(last["channel"])
        await channel_bridge.send_approval_request(last["chat_id"], approval)

        assert len(bridge.sent_approvals) == 1
        assert bridge.sent_approvals[0][1].risk_level == RiskLevel.CRITICAL

"""Tests for the HITL approval gate.

Module under test: nightowl/hitl/gate.py
Uses FakeEventBus from conftest (in-memory, same interface as Redis EventBus).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from nightowl.models.approval import ApprovalDecision, RiskLevel
from nightowl.hitl.gate import HITLGate
from nightowl.sessions.manager import SessionManager


# ---------------------------------------------------------------------------
# Approval flow: approve, reject
# ---------------------------------------------------------------------------


class TestApprovalFlow:
    async def test_approved_returns_approve_result(self, manager_with_broadcast):
        manager, bus = manager_with_broadcast
        session = await manager.create_main_session("task")
        gate = HITLGate(manager=manager, event_bus=bus)

        async def auto_approve():
            async for event in bus.subscribe(types={"approval:required"}):
                gate.resolve_approval(event["approval_id"], decision=ApprovalDecision.APPROVE)
                break

        task = asyncio.create_task(auto_approve())
        result = await gate.request_approval(
            session_id=session.id,
            tool_name="GMAIL_SEND",
            tool_args={"to": "alice@example.com"},
            risk_level=RiskLevel.HIGH,
        )
        await task
        assert result.decision == ApprovalDecision.APPROVE

    async def test_rejected_returns_reject_result(self, manager_with_broadcast):
        manager, bus = manager_with_broadcast
        session = await manager.create_main_session("task")
        gate = HITLGate(manager=manager, event_bus=bus)

        async def auto_reject():
            async for event in bus.subscribe(types={"approval:required"}):
                gate.resolve_approval(
                    event["approval_id"],
                    decision=ApprovalDecision.REJECT,
                    reason="Too risky",
                )
                break

        task = asyncio.create_task(auto_reject())
        result = await gate.request_approval(
            session_id=session.id,
            tool_name="DATABASE_DELETE",
            tool_args={"table": "users"},
            risk_level=RiskLevel.CRITICAL,
        )
        await task
        assert result.decision == ApprovalDecision.REJECT
        assert result.reason == "Too risky"

    async def test_redirect_returns_redirect_result(self, manager_with_broadcast):
        manager, bus = manager_with_broadcast
        session = await manager.create_main_session("task")
        gate = HITLGate(manager=manager, event_bus=bus, timeout_seconds=5)

        async def auto_redirect():
            async for event in bus.subscribe(types={"approval:required"}):
                gate.resolve_approval(
                    event["approval_id"],
                    decision=ApprovalDecision.REDIRECT,
                    reason="Use a different workflow",
                    redirect_message="Ask the user for a safer destination first.",
                )
                break

        task = asyncio.create_task(auto_redirect())
        result = await gate.request_approval(
            session_id=session.id,
            tool_name="GMAIL_SEND",
            tool_args={},
            risk_level=RiskLevel.HIGH,
        )
        await task
        assert result.decision == ApprovalDecision.REDIRECT
        assert result.redirect_message == "Ask the user for a safer destination first."
    async def test_first_response_wins_approve(self, manager_with_broadcast):
        manager, bus = manager_with_broadcast
        session = await manager.create_main_session("task")
        gate = HITLGate(manager=manager, event_bus=bus)

        async def double_resolve():
            async for event in bus.subscribe(types={"approval:required"}):
                gate.resolve_approval(event["approval_id"], decision=ApprovalDecision.APPROVE)
                gate.resolve_approval(event["approval_id"], decision=ApprovalDecision.REJECT)
                break

        task = asyncio.create_task(double_resolve())
        result = await gate.request_approval(
            session_id=session.id,
            tool_name="TOOL",
            tool_args={},
            risk_level=RiskLevel.HIGH,
        )
        await task
        assert result.decision == ApprovalDecision.APPROVE

    async def test_first_response_wins_reject(self, manager_with_broadcast):
        manager, bus = manager_with_broadcast
        session = await manager.create_main_session("task")
        gate = HITLGate(manager=manager, event_bus=bus)

        async def double_resolve():
            async for event in bus.subscribe(types={"approval:required"}):
                gate.resolve_approval(event["approval_id"], decision=ApprovalDecision.REJECT)
                gate.resolve_approval(event["approval_id"], decision=ApprovalDecision.APPROVE)
                break

        task = asyncio.create_task(double_resolve())
        result = await gate.request_approval(
            session_id=session.id,
            tool_name="TOOL",
            tool_args={},
            risk_level=RiskLevel.HIGH,
        )
        await task
        assert result.decision == ApprovalDecision.REJECT


# ---------------------------------------------------------------------------
# Broadcast event content
# ---------------------------------------------------------------------------


class TestBroadcastEvents:
    async def test_approval_required_event_has_all_fields(self, manager_with_broadcast):
        manager, bus = manager_with_broadcast
        session = await manager.create_main_session("task")
        gate = HITLGate(manager=manager, event_bus=bus)

        async def capture_and_resolve():
            async for event in bus.subscribe(types={"approval:required"}):
                assert event["type"] == "approval:required"
                assert "approval_id" in event
                assert event["session_id"] == session.id
                assert event["tool_name"] == "GMAIL_SEND"
                assert event["tool_args"] == {"to": "bob@example.com"}
                assert str(event["risk_level"]) == str(RiskLevel.HIGH)
                gate.resolve_approval(event["approval_id"], decision=ApprovalDecision.APPROVE)
                break

        task = asyncio.create_task(capture_and_resolve())
        await gate.request_approval(
            session_id=session.id,
            tool_name="GMAIL_SEND",
            tool_args={"to": "bob@example.com"},
            risk_level=RiskLevel.HIGH,
        )
        await task

    async def test_resolved_event_emitted_on_approve(self, manager_with_broadcast):
        manager, bus = manager_with_broadcast
        session = await manager.create_main_session("task")
        gate = HITLGate(manager=manager, event_bus=bus)

        async def resolve_and_capture():
            async for event in bus.subscribe(types={"approval:required"}):
                gate.resolve_approval(event["approval_id"], decision=ApprovalDecision.APPROVE)
                break
            await asyncio.sleep(0.05)
            events = bus.drain()
            resolved = [e for e in events if e.get("type") == "approval:resolved"]
            assert len(resolved) >= 1
            assert resolved[0]["decision"] == ApprovalDecision.APPROVE

        task = asyncio.create_task(resolve_and_capture())
        await gate.request_approval(
            session_id=session.id,
            tool_name="TOOL",
            tool_args={},
            risk_level=RiskLevel.HIGH,
        )
        await task


# ---------------------------------------------------------------------------
# Approval request IDs
# ---------------------------------------------------------------------------


class TestApprovalIDs:
    async def test_approval_id_has_prefix(self, manager_with_broadcast):
        manager, bus = manager_with_broadcast
        session = await manager.create_main_session("task")
        gate = HITLGate(manager=manager, event_bus=bus)

        async def capture_id():
            async for event in bus.subscribe(types={"approval:required"}):
                assert event["approval_id"].startswith("approval:")
                gate.resolve_approval(event["approval_id"], decision=ApprovalDecision.APPROVE)
                break

        task = asyncio.create_task(capture_id())
        await gate.request_approval(
            session_id=session.id, tool_name="TOOL", tool_args={}, risk_level=RiskLevel.HIGH,
        )
        await task

    async def test_consecutive_requests_get_distinct_ids(self, manager_with_broadcast):
        manager, bus = manager_with_broadcast
        session = await manager.create_main_session("task")
        gate = HITLGate(manager=manager, event_bus=bus)
        captured_ids: list[str] = []

        async def auto_resolve():
            count = 0
            async for event in bus.subscribe(types={"approval:required"}):
                captured_ids.append(event["approval_id"])
                gate.resolve_approval(event["approval_id"], decision=ApprovalDecision.APPROVE)
                count += 1
                if count >= 2:
                    break

        task = asyncio.create_task(auto_resolve())
        await gate.request_approval(
            session_id=session.id, tool_name="A", tool_args={}, risk_level=RiskLevel.HIGH,
        )
        await gate.request_approval(
            session_id=session.id, tool_name="B", tool_args={}, risk_level=RiskLevel.HIGH,
        )
        await task

        assert len(captured_ids) == 2
        assert captured_ids[0] != captured_ids[1]


# ---------------------------------------------------------------------------
# resolve_approval edge cases
# ---------------------------------------------------------------------------


class TestResolveEdgeCases:
    async def test_resolve_unknown_id_does_not_crash(self, manager: SessionManager):
        gate = HITLGate(manager=manager)
        gate.resolve_approval("approval:nonexistent", decision=ApprovalDecision.APPROVE)

    async def test_resolve_reason_surfaces_in_resolved_event(self, manager_with_broadcast):
        manager, bus = manager_with_broadcast
        session = await manager.create_main_session("task")
        gate = HITLGate(manager=manager, event_bus=bus)

        async def reject_with_reason():
            async for event in bus.subscribe(types={"approval:required"}):
                gate.resolve_approval(
                    event["approval_id"],
                    decision=ApprovalDecision.REJECT,
                    reason="Not authorized for payments",
                )
                break
            await asyncio.sleep(0.05)
            events = bus.drain()
            resolved = [e for e in events if e.get("type") == "approval:resolved"]
            assert len(resolved) >= 1
            assert resolved[0].get("reason") == "Not authorized for payments"

        task = asyncio.create_task(reject_with_reason())
        await gate.request_approval(
            session_id=session.id,
            tool_name="STRIPE_CHARGE",
            tool_args={"amount": 100},
            risk_level=RiskLevel.CRITICAL,
        )
        await task


# ---------------------------------------------------------------------------
# Channel delivery
# ---------------------------------------------------------------------------


class TestChannelDelivery:
    async def test_no_channel_does_not_prevent_broadcast(self, manager_with_broadcast):
        manager, bus = manager_with_broadcast
        session = await manager.create_main_session("task")
        gate = HITLGate(manager=manager, event_bus=bus)

        async def approve_via_bus():
            async for event in bus.subscribe(types={"approval:required"}):
                assert event["type"] == "approval:required"
                gate.resolve_approval(event["approval_id"], decision=ApprovalDecision.APPROVE)
                break

        task = asyncio.create_task(approve_via_bus())
        result = await gate.request_approval(
            session_id=session.id,
            tool_name="TOOL",
            tool_args={},
            risk_level=RiskLevel.HIGH,
        )
        await task
        assert result.decision == ApprovalDecision.APPROVE

    async def test_channel_delivery_attempted_when_channel_set(self, manager_with_broadcast):
        manager, bus = manager_with_broadcast
        session = await manager.create_main_session("task")
        gate = HITLGate(manager=manager, event_bus=bus)

        async def auto_approve():
            async for event in bus.subscribe(types={"approval:required"}):
                gate.resolve_approval(event["approval_id"], decision=ApprovalDecision.APPROVE)
                break

        with patch.object(gate, "_send_channel_approval", new_callable=AsyncMock) as mock_send:
            gate.set_last_channel(session.id, channel="telegram", chat_id="12345")
            task = asyncio.create_task(auto_approve())
            await gate.request_approval(
                session_id=session.id,
                tool_name="GMAIL_SEND",
                tool_args={"to": "alice@example.com"},
                risk_level=RiskLevel.HIGH,
            )
            await task

        mock_send.assert_called_once()
class TestRedirectFlow:
    async def test_redirect_consumes_next_message_as_new_direction(self, manager: SessionManager):
        gate = HITLGate(manager=manager, timeout_seconds=5)
        session = await manager.create_main_session("task")

        gate._pending_redirects[session.id] = {  # type: ignore[attr-defined]
            "approval_id": "approval:test",
            "tool_name": "GMAIL_SEND",
        }

        redirected = gate.consume_redirect_instruction(session.id, "Use a draft instead")

        assert redirected is not None
        assert "GMAIL_SEND" in redirected
        assert "Use a draft instead" in redirected

    async def test_handle_text_response_parses_redirect_command(self, manager_with_broadcast):
        manager, bus = manager_with_broadcast
        session = await manager.create_main_session("task")
        gate = HITLGate(manager=manager, event_bus=bus, timeout_seconds=5)

        request_task = asyncio.create_task(gate.request_approval(
            session_id=session.id,
            tool_name="TOOL",
            tool_args={},
            risk_level=RiskLevel.HIGH,
        ))
        await asyncio.sleep(0)

        assert gate.handle_text_response("REDIRECT approval:test") is False

        events = bus.drain()
        approval_ids = [e["approval_id"] for e in events if e.get("type") == "approval:required"]
        assert len(approval_ids) == 1
        assert gate.handle_text_response(f"REDIRECT {approval_ids[0]}") is True

        result = await request_task
        assert result.decision == ApprovalDecision.REDIRECT

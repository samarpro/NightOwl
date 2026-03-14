"""Tests for the SMS bridge.

Module under test: nightowl/channels/sms.py

SMSBridge(ChannelBridge) uses Twilio SMS API. Webhook ingress.
normalize_inbound parses Twilio webhook. send_message via Twilio.
send_approval_request as text with APPROVE/REJECT reply instructions.

SMS has no inline keyboards — approval is text-based with reply commands.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from nightowl.models.message import ChannelMessage
from nightowl.models.approval import ApprovalRequest, RiskLevel
from nightowl.channels.sms import SMSBridge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_twilio_sms_payload(
    from_number: str = "+61400111222",
    body: str = "Plan a night out",
    message_sid: str = "SM0987654321fedcba",
) -> dict[str, str]:
    """Simulate a Twilio SMS webhook payload."""
    return {
        "MessageSid": message_sid,
        "From": from_number,
        "Body": body,
        "To": "+61400000000",
    }


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestSMSBridgeConstruction:
    def test_channel_id_is_sms(self):
        with patch("nightowl.channels.sms._get_twilio_client"):
            bridge = SMSBridge()
        assert bridge.channel_id == "sms"


# ---------------------------------------------------------------------------
# Inbound normalization
# ---------------------------------------------------------------------------


class TestSMSNormalize:
    def test_normalizes_twilio_sms_payload(self):
        with patch("nightowl.channels.sms._get_twilio_client"):
            bridge = SMSBridge()

        raw = _make_twilio_sms_payload(from_number="+61400111222", body="Check my calendar")
        msg = bridge.normalize_inbound(raw)

        assert isinstance(msg, ChannelMessage)
        assert msg.channel == "sms"
        assert msg.sender_id == "+61400111222"
        assert msg.text == "Check my calendar"

    def test_no_whatsapp_prefix_on_sms(self):
        """SMS numbers don't have the whatsapp: prefix."""
        with patch("nightowl.channels.sms._get_twilio_client"):
            bridge = SMSBridge()

        raw = _make_twilio_sms_payload(from_number="+61400999888")
        msg = bridge.normalize_inbound(raw)
        assert not msg.sender_id.startswith("whatsapp:")

    def test_thread_id_is_none_for_sms(self):
        """SMS has no threading concept."""
        with patch("nightowl.channels.sms._get_twilio_client"):
            bridge = SMSBridge()

        raw = _make_twilio_sms_payload()
        msg = bridge.normalize_inbound(raw)
        assert msg.thread_id is None


# ---------------------------------------------------------------------------
# Outbound: send_message
# ---------------------------------------------------------------------------


class TestSMSSendMessage:
    async def test_calls_twilio_create_message(self):
        with patch("nightowl.channels.sms._get_twilio_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client_fn.return_value = mock_client
            bridge = SMSBridge()

        mock_client.messages.create = MagicMock()
        await bridge.send_message("+61400111222", "Your reservation is confirmed")

        mock_client.messages.create.assert_called_once()
        call_str = str(mock_client.messages.create.call_args)
        assert "+61400111222" in call_str
        assert "reservation is confirmed" in call_str

    async def test_does_not_add_whatsapp_prefix(self):
        """SMS should send to raw phone number, no whatsapp: prefix."""
        with patch("nightowl.channels.sms._get_twilio_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client_fn.return_value = mock_client
            bridge = SMSBridge()

        mock_client.messages.create = MagicMock()
        await bridge.send_message("+61400111222", "test")

        call_str = str(mock_client.messages.create.call_args)
        assert "whatsapp:" not in call_str


# ---------------------------------------------------------------------------
# Outbound: send_approval_request (text-based, no inline keyboard)
# ---------------------------------------------------------------------------


class TestSMSSendApproval:
    async def test_approval_sent_as_text_message(self):
        """SMS has no inline keyboards — approval must be a plain text message."""
        with patch("nightowl.channels.sms._get_twilio_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client_fn.return_value = mock_client
            bridge = SMSBridge()

        mock_client.messages.create = MagicMock()
        approval = ApprovalRequest(
            id="approval:sms123",
            session_id="session:1",
            tool_name="GMAIL_SEND",
            tool_args={"to": "alice@example.com"},
            risk_level=RiskLevel.HIGH,
        )
        await bridge.send_approval_request("+61400111222", approval)

        mock_client.messages.create.assert_called_once()

    async def test_approval_text_contains_tool_info(self):
        with patch("nightowl.channels.sms._get_twilio_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client_fn.return_value = mock_client
            bridge = SMSBridge()

        mock_client.messages.create = MagicMock()
        approval = ApprovalRequest(
            id="approval:sms456",
            session_id="session:1",
            tool_name="STRIPE_CHARGE",
            tool_args={"amount": 100},
            risk_level=RiskLevel.CRITICAL,
        )
        await bridge.send_approval_request("+61400111222", approval)

        call_str = str(mock_client.messages.create.call_args)
        assert "STRIPE_CHARGE" in call_str

    async def test_approval_text_has_reply_instructions(self):
        """SMS approval must tell the user how to reply (e.g. 'Reply APPROVE or REJECT')."""
        with patch("nightowl.channels.sms._get_twilio_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client_fn.return_value = mock_client
            bridge = SMSBridge()

        mock_client.messages.create = MagicMock()
        approval = ApprovalRequest(
            id="approval:sms789",
            session_id="session:1",
            tool_name="TOOL",
            risk_level=RiskLevel.HIGH,
        )
        await bridge.send_approval_request("+61400111222", approval)

        call_str = str(mock_client.messages.create.call_args).lower()
        # Must include reply instructions since SMS has no buttons
        assert "approve" in call_str
        assert "reject" in call_str

    async def test_approval_text_contains_approval_id(self):
        """The approval ID must be in the message so reply parsing can match it."""
        with patch("nightowl.channels.sms._get_twilio_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client_fn.return_value = mock_client
            bridge = SMSBridge()

        mock_client.messages.create = MagicMock()
        approval = ApprovalRequest(
            id="approval:smsdeadbeef",
            session_id="session:1",
            tool_name="TOOL",
            risk_level=RiskLevel.HIGH,
        )
        await bridge.send_approval_request("+61400111222", approval)

        call_str = str(mock_client.messages.create.call_args)
        assert "smsdeadbeef" in call_str

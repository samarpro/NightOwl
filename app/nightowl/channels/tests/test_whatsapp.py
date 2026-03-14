"""Tests for the WhatsApp bridge.

Module under test: nightowl/channels/whatsapp.py

WhatsAppBridge(ChannelBridge) uses Twilio WhatsApp Business API.
Webhook ingress. normalize_inbound parses Twilio webhook payload.
send_message via Twilio client. send_approval_request via interactive buttons.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nightowl.models.message import ChannelMessage
from nightowl.models.approval import ApprovalRequest, RiskLevel
from nightowl.channels.whatsapp import WhatsAppBridge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_twilio_whatsapp_payload(
    from_number: str = "whatsapp:+61400111222",
    body: str = "Plan a night out",
    message_sid: str = "SM1234567890abcdef",
) -> dict[str, str]:
    """Simulate a Twilio WhatsApp webhook payload (form-encoded, received as dict)."""
    return {
        "MessageSid": message_sid,
        "From": from_number,
        "Body": body,
        "To": "whatsapp:+61400000000",
        "NumMedia": "0",
    }


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestWhatsAppBridgeConstruction:
    def test_channel_id_is_whatsapp(self):
        with patch("nightowl.channels.whatsapp._get_twilio_client"):
            bridge = WhatsAppBridge()
        assert bridge.channel_id == "whatsapp"


# ---------------------------------------------------------------------------
# Inbound normalization
# ---------------------------------------------------------------------------


class TestWhatsAppNormalize:
    def test_normalizes_twilio_payload(self):
        with patch("nightowl.channels.whatsapp._get_twilio_client"):
            bridge = WhatsAppBridge()

        raw = _make_twilio_whatsapp_payload(
            from_number="whatsapp:+61400111222",
            body="Book a restaurant",
        )
        msg = bridge.normalize_inbound(raw)

        assert isinstance(msg, ChannelMessage)
        assert msg.channel == "whatsapp"
        assert msg.text == "Book a restaurant"

    def test_sender_id_strips_whatsapp_prefix(self):
        """Twilio sends 'whatsapp:+61...' — bridge should normalize to just the number."""
        with patch("nightowl.channels.whatsapp._get_twilio_client"):
            bridge = WhatsAppBridge()

        raw = _make_twilio_whatsapp_payload(from_number="whatsapp:+61400111222")
        msg = bridge.normalize_inbound(raw)

        # Should be the phone number without the whatsapp: prefix
        assert msg.sender_id == "+61400111222"

    def test_empty_body_normalized(self):
        with patch("nightowl.channels.whatsapp._get_twilio_client"):
            bridge = WhatsAppBridge()

        raw = _make_twilio_whatsapp_payload(body="")
        msg = bridge.normalize_inbound(raw)
        assert msg.text == ""


# ---------------------------------------------------------------------------
# Outbound: send_message
# ---------------------------------------------------------------------------


class TestWhatsAppSendMessage:
    async def test_calls_twilio_create_message(self):
        with patch("nightowl.channels.whatsapp._get_twilio_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client_fn.return_value = mock_client
            bridge = WhatsAppBridge()

        # Twilio's messages.create is sync but we may wrap it
        mock_create = MagicMock()
        mock_client.messages.create = mock_create

        await bridge.send_message("+61400111222", "Your table is booked!")

        mock_create.assert_called_once()
        call_str = str(mock_create.call_args)
        assert "+61400111222" in call_str or "whatsapp:+61400111222" in call_str
        assert "table is booked" in call_str

    async def test_prepends_whatsapp_prefix_to_recipient(self):
        """Twilio requires 'whatsapp:+...' format for the To field."""
        with patch("nightowl.channels.whatsapp._get_twilio_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client_fn.return_value = mock_client
            bridge = WhatsAppBridge()

        mock_client.messages.create = MagicMock()
        await bridge.send_message("+61400111222", "test")

        call_str = str(mock_client.messages.create.call_args)
        assert "whatsapp:" in call_str


# ---------------------------------------------------------------------------
# Outbound: send_approval_request (interactive buttons)
# ---------------------------------------------------------------------------


class TestWhatsAppSendApproval:
    async def test_approval_message_contains_tool_info(self):
        with patch("nightowl.channels.whatsapp._get_twilio_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client_fn.return_value = mock_client
            bridge = WhatsAppBridge()

        mock_client.messages.create = MagicMock()
        approval = ApprovalRequest(
            id="approval:wa123",
            session_id="session:1",
            tool_name="STRIPE_CHARGE",
            tool_args={"amount": 50},
            risk_level=RiskLevel.CRITICAL,
        )
        await bridge.send_approval_request("+61400111222", approval)

        mock_client.messages.create.assert_called_once()
        call_str = str(mock_client.messages.create.call_args)
        assert "STRIPE_CHARGE" in call_str

    async def test_approval_message_has_approve_reject_and_redirect_options(self):
        with patch("nightowl.channels.whatsapp._get_twilio_client") as mock_client_fn:
            mock_client = MagicMock()
            mock_client_fn.return_value = mock_client
            bridge = WhatsAppBridge()

        mock_client.messages.create = MagicMock()
        approval = ApprovalRequest(
            id="approval:wa456",
            session_id="session:1",
            tool_name="TOOL",
            risk_level=RiskLevel.HIGH,
        )
        await bridge.send_approval_request("+61400111222", approval)

        call_str = str(mock_client.messages.create.call_args).lower()
        assert "approve" in call_str or "allow" in call_str or "yes" in call_str
        assert "reject" in call_str or "deny" in call_str or "no" in call_str
        assert "redirect" in call_str

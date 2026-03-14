"""Tests for the Telegram bridge.

Module under test: nightowl/channels/telegram.py

TelegramBridge(ChannelBridge) uses python-telegram-bot. On inbound message:
normalize to ChannelMessage and call gateway ingest. Outbound: send_message
via Bot API, send_approval_request via inline keyboard with approve/reject.

These tests mock the telegram Bot API — no network calls.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nightowl.models.message import ChannelMessage
from nightowl.models.approval import ApprovalRequest, RiskLevel
from nightowl.channels.telegram import TelegramBridge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_telegram_update(
    chat_id: int = 12345,
    user_id: int = 67890,
    text: str = "Plan a night out",
    message_id: int = 1,
    thread_id: int | None = None,
) -> dict[str, Any]:
    """Simulate the shape of a Telegram Update's message payload."""
    return {
        "message_id": message_id,
        "chat": {"id": chat_id, "type": "private"},
        "from": {"id": user_id, "first_name": "Test"},
        "text": text,
        "message_thread_id": thread_id,
    }


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestTelegramBridgeConstruction:
    def test_channel_id_is_telegram(self):
        with patch("nightowl.channels.telegram._get_bot_token", return_value="fake:token"):
            bridge = TelegramBridge()
        assert bridge.channel_id == "telegram"


# ---------------------------------------------------------------------------
# Inbound normalization
# ---------------------------------------------------------------------------


class TestTelegramNormalize:
    def test_normalizes_text_message(self):
        with patch("nightowl.channels.telegram._get_bot_token", return_value="fake:token"):
            bridge = TelegramBridge()

        raw = _make_telegram_update(chat_id=111, user_id=222, text="Hello agent")
        msg = bridge.normalize_inbound(raw)

        assert isinstance(msg, ChannelMessage)
        assert msg.channel == "telegram"
        assert msg.sender_id == "222"
        assert msg.text == "Hello agent"

    def test_sender_id_is_string(self):
        """Telegram user IDs are ints — bridge must convert to string."""
        with patch("nightowl.channels.telegram._get_bot_token", return_value="fake:token"):
            bridge = TelegramBridge()

        raw = _make_telegram_update(user_id=99887766)
        msg = bridge.normalize_inbound(raw)
        assert isinstance(msg.sender_id, str)

    def test_preserves_thread_id(self):
        with patch("nightowl.channels.telegram._get_bot_token", return_value="fake:token"):
            bridge = TelegramBridge()

        raw = _make_telegram_update(thread_id=42)
        msg = bridge.normalize_inbound(raw)
        assert msg.thread_id == "42" or msg.thread_id == 42  # str or int, both acceptable

    def test_no_thread_id_is_none(self):
        with patch("nightowl.channels.telegram._get_bot_token", return_value="fake:token"):
            bridge = TelegramBridge()

        raw = _make_telegram_update(thread_id=None)
        msg = bridge.normalize_inbound(raw)
        assert msg.thread_id is None

    def test_empty_text_normalized(self):
        with patch("nightowl.channels.telegram._get_bot_token", return_value="fake:token"):
            bridge = TelegramBridge()

        raw = _make_telegram_update(text="")
        msg = bridge.normalize_inbound(raw)
        assert msg.text == ""


# ---------------------------------------------------------------------------
# Outbound: send_message
# ---------------------------------------------------------------------------


class TestTelegramSendMessage:
    async def test_calls_bot_send_message(self):
        with patch("nightowl.channels.telegram._get_bot_token", return_value="fake:token"):
            bridge = TelegramBridge()

        bridge._bot = MagicMock()
        bridge._bot.send_message = AsyncMock()

        await bridge.send_message("12345", "Your reservation is confirmed")

        bridge._bot.send_message.assert_called_once()
        call_kwargs = bridge._bot.send_message.call_args
        call_str = str(call_kwargs)
        assert "12345" in call_str or 12345 in (call_kwargs[0] if call_kwargs[0] else ())
        assert "reservation is confirmed" in call_str

    async def test_sends_to_correct_chat_id(self):
        with patch("nightowl.channels.telegram._get_bot_token", return_value="fake:token"):
            bridge = TelegramBridge()

        bridge._bot = MagicMock()
        bridge._bot.send_message = AsyncMock()

        await bridge.send_message("99999", "test")

        call_str = str(bridge._bot.send_message.call_args)
        assert "99999" in call_str


# ---------------------------------------------------------------------------
# Outbound: send_approval_request (inline keyboard)
# ---------------------------------------------------------------------------


class TestTelegramSendApproval:
    async def test_sends_inline_keyboard(self):
        with patch("nightowl.channels.telegram._get_bot_token", return_value="fake:token"):
            bridge = TelegramBridge()

        bridge._bot = MagicMock()
        bridge._bot.send_message = AsyncMock()

        approval = ApprovalRequest(
            id="approval:abc123",
            session_id="session:x",
            tool_name="GMAIL_SEND",
            tool_args={"to": "alice@example.com"},
            risk_level=RiskLevel.HIGH,
        )
        await bridge.send_approval_request("12345", approval)

        bridge._bot.send_message.assert_called_once()
        call_kwargs = bridge._bot.send_message.call_args
        call_str = str(call_kwargs)
        # Must include reply_markup with inline keyboard
        assert "reply_markup" in call_str or "InlineKeyboard" in call_str

    async def test_approval_message_contains_tool_info(self):
        with patch("nightowl.channels.telegram._get_bot_token", return_value="fake:token"):
            bridge = TelegramBridge()

        bridge._bot = MagicMock()
        bridge._bot.send_message = AsyncMock()

        approval = ApprovalRequest(
            id="approval:xyz",
            session_id="session:1",
            tool_name="STRIPE_CHARGE",
            tool_args={"amount": 99, "currency": "usd"},
            risk_level=RiskLevel.CRITICAL,
        )
        await bridge.send_approval_request("12345", approval)

        call_str = str(bridge._bot.send_message.call_args)
        assert "STRIPE_CHARGE" in call_str
        assert "critical" in call_str.lower() or "CRITICAL" in call_str

    async def test_approval_keyboard_has_approve_reject_and_redirect(self):
        with patch("nightowl.channels.telegram._get_bot_token", return_value="fake:token"):
            bridge = TelegramBridge()

        bridge._bot = MagicMock()
        bridge._bot.send_message = AsyncMock()

        approval = ApprovalRequest(
            id="approval:test",
            session_id="session:1",
            tool_name="TOOL",
            risk_level=RiskLevel.HIGH,
        )
        await bridge.send_approval_request("12345", approval)

        call_str = str(bridge._bot.send_message.call_args).lower()
        # Inline keyboard must have approve, reject, and redirect options
        assert "approve" in call_str or "allow" in call_str or "yes" in call_str
        assert "reject" in call_str or "deny" in call_str or "no" in call_str
        assert "redirect" in call_str

    async def test_approval_callback_data_contains_approval_id(self):
        """The inline keyboard callback_data must embed the approval_id so we can resolve it."""
        with patch("nightowl.channels.telegram._get_bot_token", return_value="fake:token"):
            bridge = TelegramBridge()

        bridge._bot = MagicMock()
        bridge._bot.send_message = AsyncMock()

        approval = ApprovalRequest(
            id="approval:deadbeef",
            session_id="session:1",
            tool_name="TOOL",
            risk_level=RiskLevel.HIGH,
        )
        await bridge.send_approval_request("12345", approval)

        call_str = str(bridge._bot.send_message.call_args)
        assert "deadbeef" in call_str


# ---------------------------------------------------------------------------
# Bot API errors
# ---------------------------------------------------------------------------


class TestTelegramErrorHandling:
    async def test_send_message_bot_error_does_not_crash(self):
        """If the Bot API fails, send_message should raise or return error — not hang."""
        with patch("nightowl.channels.telegram._get_bot_token", return_value="fake:token"):
            bridge = TelegramBridge()

        bridge._bot = MagicMock()
        bridge._bot.send_message = AsyncMock(side_effect=Exception("Telegram API timeout"))

        with pytest.raises(Exception, match="Telegram API timeout"):
            await bridge.send_message("12345", "test")

    async def test_send_approval_bot_error_does_not_crash(self):
        with patch("nightowl.channels.telegram._get_bot_token", return_value="fake:token"):
            bridge = TelegramBridge()

        bridge._bot = MagicMock()
        bridge._bot.send_message = AsyncMock(side_effect=Exception("Telegram API timeout"))

        approval = ApprovalRequest(
            id="approval:err",
            session_id="session:1",
            tool_name="TOOL",
            risk_level=RiskLevel.HIGH,
        )
        with pytest.raises(Exception, match="Telegram API timeout"):
            await bridge.send_approval_request("12345", approval)

from __future__ import annotations

from nightowl.channels.telegram.normalize import normalize_telegram_update
from nightowl.channels.telegram.schemas import TelegramUpdate
from nightowl.channels.telegram.verify import verify_telegram_secret


class TestTelegramVerify:
    def test_verifies_matching_secret(self):
        assert verify_telegram_secret("secret", "secret") is True

    def test_rejects_wrong_secret(self):
        assert verify_telegram_secret("bad", "secret") is False


class TestTelegramNormalize:
    def test_normalizes_text_message(self):
        update = TelegramUpdate.model_validate({
            "update_id": 99,
            "message": {
                "message_id": 123,
                "from": {"id": 456, "first_name": "Sam", "username": "sam"},
                "chat": {"id": -10001, "type": "supergroup"},
                "text": "hello",
                "message_thread_id": 777,
            },
        })

        message = normalize_telegram_update(update)
        assert message is not None
        assert message.channel == "telegram"
        assert message.sender_id == "456"
        assert message.chat_id == "-10001"
        assert message.thread_id == "777"
        assert message.message_id == "123"
        assert message.metadata["chat_type"] == "supergroup"

    def test_ignores_non_text_updates(self):
        update = TelegramUpdate.model_validate({
            "message": {
                "message_id": 123,
                "from": {"id": 456},
                "chat": {"id": 1, "type": "private"},
            },
        })
        assert normalize_telegram_update(update) is None

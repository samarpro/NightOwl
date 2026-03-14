from __future__ import annotations

import anyio
from fastapi.testclient import TestClient

from nightowl.main import create_app


class TestApi:
    def test_health(self):
        with TestClient(create_app()) as client:
            response = client.get("/api/v1/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    def test_telegram_webhook_rejects_bad_secret(self):
        app = create_app()
        app.state.settings.telegram_webhook_secret = "expected"
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/channels/telegram/webhook",
                json={},
                headers={"x-telegram-bot-api-secret-token": "wrong"},
            )
            assert response.status_code == 401

    def test_websocket_streams_translated_events(self):
        app = create_app()
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as websocket:
                client.portal.call(
                    client.app.state.broadcaster.publish,
                    {
                        "type": "approval:required",
                        "approval_id": "approval:test",
                        "session_id": "session:test",
                        "tool_name": "TOOL",
                        "tool_args": {},
                        "risk_level": "high",
                        "expires_at": "2026-03-14T00:00:00Z",
                    },
                )
                event = websocket.receive_json()
                assert event["event_type"] == "approval.requested"

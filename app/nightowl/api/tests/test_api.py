from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import delete

from nightowl.db import SessionRow
from nightowl.config import settings
from nightowl.main import create_app


class TestApi:
    def test_health(self):
        with TestClient(create_app()) as client:
            response = client.get("/api/v1/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    def test_telegram_webhook_rejects_bad_secret(self):
        app = create_app()
        original_secret = settings.telegram_webhook_secret
        settings.telegram_webhook_secret = "expected"
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/channels/telegram/webhook",
                    json={},
                    headers={"x-telegram-bot-api-secret-token": "wrong"},
                )
                assert response.status_code == 401
        finally:
            settings.telegram_webhook_secret = original_secret

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

    def test_sessions_endpoint_lists_root_sessions_by_default(self):
        app = create_app()
        root_session_id = "session:test-root"
        child_session_id = "session:test-child"

        with TestClient(app) as client:
            client.portal.call(_delete_sessions, client.app.state.session_factory, [root_session_id, child_session_id])
            client.portal.call(
                _insert_sessions,
                client.app.state.session_factory,
                [
                    {"id": root_session_id, "parent_id": None, "task": "Root task", "role": "main", "depth": 0},
                    {"id": child_session_id, "parent_id": root_session_id, "task": "Child task", "role": "leaf", "depth": 1},
                ],
            )

            response = client.get("/api/v1/sessions/")

            client.portal.call(_delete_sessions, client.app.state.session_factory, [root_session_id, child_session_id])

        assert response.status_code == 200
        body = response.json()
        assert any(session["id"] == root_session_id for session in body)
        assert all(session["id"] != child_session_id for session in body)

    def test_sessions_endpoint_filters_by_parent_id(self):
        app = create_app()
        parent_session_id = "session:test-parent"
        child_session_ids = ["session:test-child-a", "session:test-child-b"]
        other_child_session_id = "session:test-child-other"

        with TestClient(app) as client:
            client.portal.call(
                _delete_sessions,
                client.app.state.session_factory,
                [parent_session_id, *child_session_ids, other_child_session_id, "session:test-parent-other"],
            )
            client.portal.call(
                _insert_sessions,
                client.app.state.session_factory,
                [
                    {"id": parent_session_id, "parent_id": None, "task": "Parent", "role": "main", "depth": 0},
                    {"id": "session:test-parent-other", "parent_id": None, "task": "Other parent", "role": "main", "depth": 0},
                    {"id": child_session_ids[0], "parent_id": parent_session_id, "task": "Child A", "role": "leaf", "depth": 1},
                    {"id": child_session_ids[1], "parent_id": parent_session_id, "task": "Child B", "role": "leaf", "depth": 1},
                    {"id": other_child_session_id, "parent_id": "session:test-parent-other", "task": "Other child", "role": "leaf", "depth": 1},
                ],
            )

            response = client.get(f"/api/v1/sessions/?parentId={parent_session_id}")

            client.portal.call(
                _delete_sessions,
                client.app.state.session_factory,
                [parent_session_id, *child_session_ids, other_child_session_id, "session:test-parent-other"],
            )

        assert response.status_code == 200
        body = response.json()
        assert {session["id"] for session in body} == set(child_session_ids)
        assert all(session["parentId"] == parent_session_id for session in body)


async def _insert_sessions(session_factory, sessions: list[dict[str, object]]) -> None:
    async with session_factory() as db:
        for session in sessions:
            db.add(SessionRow(**session))
        await db.commit()


async def _delete_sessions(session_factory, session_ids: list[str]) -> None:
    async with session_factory() as db:
        await db.execute(delete(SessionRow).where(SessionRow.id.in_(session_ids)))
        await db.commit()

"""Telegram webhook router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from nightowl.channels.telegram.normalize import normalize_telegram_update
from nightowl.channels.telegram.schemas import TelegramUpdate
from nightowl.channels.telegram.verify import verify_telegram_secret

router = APIRouter(prefix="/api/v1/channels/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(request: Request) -> dict[str, object]:
    secret = request.app.state.settings.telegram_webhook_secret.strip()
    header = request.headers.get("x-telegram-bot-api-secret-token")
    if not verify_telegram_secret(header, secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")

    try:
        body = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid json") from exc

    update = TelegramUpdate.model_validate(body)
    message = normalize_telegram_update(update)
    if message is None:
        return {"ok": True, "ignored": True}

    result = await request.app.state.ingress_service.ingest(message)
    return {"ok": True, "sessionId": result.session_id, "created": result.created}

"""Centralised webhook router for channel bridges and third-party callbacks."""

from __future__ import annotations

import hmac
import logging

from fastapi import APIRouter, HTTPException, Header, Request

from nightowl.composio_tools.meta_tools import auth_waiter
from nightowl.config import settings

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["webhooks"])


# ── Telegram ──────────────────────────────────────────────────────


@router.post("/channels/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, object]:
    if settings.telegram_webhook_secret:
        if not x_telegram_bot_api_secret_token or not hmac.compare_digest(
            x_telegram_bot_api_secret_token, settings.telegram_webhook_secret,
        ):
            raise HTTPException(status_code=401, detail="Invalid secret token")

    body = await request.json()
    log.debug("Telegram webhook payload: %s", body)

    # Handle callback_query (inline keyboard button presses — e.g. HITL approvals)
    callback_query = body.get("callback_query")
    if callback_query:
        return await _handle_telegram_callback(request, callback_query)

    # Handle regular messages
    message = body.get("message")
    if not message:
        log.debug("Telegram webhook: no message or callback_query, skipping")
        return {"ok": True, "skipped": True}

    registry = request.app.state.channel_registry
    bridge = registry.get("telegram")
    if bridge is None:
        raise HTTPException(status_code=503, detail="Telegram bridge not configured")

    channel_message = bridge.normalize_inbound(message)
    log.debug("Telegram inbound message from %s: %s", channel_message.sender_id, channel_message.text)
    result = await request.app.state.ingress_service.ingest(channel_message)
    return {"ok": True, "sessionId": result.session_id, "created": result.created}


async def _handle_telegram_callback(request: Request, callback_query: dict) -> dict[str, object]:
    """Handle inline keyboard button presses (HITL approve/reject)."""
    data = callback_query.get("data", "")
    log.debug("Telegram callback_query data: %s", data)

    # callback_data format: "approve:approval_id" or "reject:approval_id"
    gate = request.app.state.hitl_gate
    if data.startswith("approve:"):
        approval_id = data[len("approve:"):]
        gate.resolve_approval(approval_id, approved=True, reason="Approved via Telegram")
        log.info("Approval %s approved via Telegram", approval_id)
    elif data.startswith("reject:"):
        approval_id = data[len("reject:"):]
        gate.resolve_approval(approval_id, approved=False, reason="Rejected via Telegram")
        log.info("Approval %s rejected via Telegram", approval_id)
    else:
        log.warning("Unknown Telegram callback_query data: %s", data)
        return {"ok": True, "skipped": True}

    # Answer the callback query to remove the loading spinner in Telegram
    registry = request.app.state.channel_registry
    bridge = registry.get("telegram")
    if bridge:
        try:
            await bridge._bot.answer_callback_query(
                callback_query["id"],
                text="Approved!" if data.startswith("approve:") else "Rejected.",
            )
        except Exception:
            log.debug("Failed to answer callback query", exc_info=True)

    return {"ok": True, "handled": True}


# ── Composio auth callback ────────────────────────────────────────


@router.get("/composio/auth/callback")
async def composio_auth_callback(
    request: Request,
    connectedAccountId: str | None = None,
    status: str | None = None,
) -> dict[str, object]:
    """Composio redirects here when a user completes an OAuth flow."""
    connection_id = connectedAccountId
    if not connection_id:
        log.warning("Composio auth callback missing connectedAccountId: %s", dict(request.query_params))
        return {"ok": False, "error": "missing connectedAccountId"}

    resolved = auth_waiter.resolve(connection_id)
    log.info("Composio auth callback for %s (status=%s) — resolved=%s", connection_id, status, resolved)
    return {"ok": True, "resolved": resolved}

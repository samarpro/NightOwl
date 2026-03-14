"""Centralised webhook router for channel bridges and third-party callbacks."""

from __future__ import annotations

import hmac
import logging

from fastapi import APIRouter, Form, HTTPException, Header, Request

from nightowl.composio_tools.meta_tools import auth_waiter
from nightowl.config import settings
from nightowl.models.approval import ApprovalDecision

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
    """Handle inline keyboard button presses (HITL approve/reject/redirect)."""
    data = callback_query.get("data", "")
    log.debug("Telegram callback_query data: %s", data)

    # callback_data format: "approve:approval_id", "reject:approval_id", or "redirect:approval_id"
    gate = request.app.state.hitl_gate
    if data.startswith("approve:"):
        approval_id = data[len("approve:"):]
        gate.resolve_approval(
            approval_id,
            decision=ApprovalDecision.APPROVE,
            reason="Approved via Telegram",
        )
        log.info("Approval %s approved via Telegram", approval_id)
    elif data.startswith("reject:"):
        approval_id = data[len("reject:"):]
        gate.resolve_approval(
            approval_id,
            decision=ApprovalDecision.REJECT,
            reason="Rejected via Telegram",
        )
        log.info("Approval %s rejected via Telegram", approval_id)
    elif data.startswith("redirect:"):
        approval_id = data[len("redirect:"):]
        gate.resolve_approval(
            approval_id,
            decision=ApprovalDecision.REDIRECT,
            reason="Redirected via Telegram",
        )
        log.info("Approval %s redirected via Telegram", approval_id)
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
                text=(
                    "Approved!"
                    if data.startswith("approve:")
                    else "Reply with the new direction."
                    if data.startswith("redirect:")
                    else "Rejected."
                ),
            )
        except Exception:
            log.debug("Failed to answer callback query", exc_info=True)

    return {"ok": True, "handled": True}


# ── WhatsApp (Twilio) ─────────────────────────────────────────────


@router.post("/channels/whatsapp/webhook")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(""),
    MessageSid: str = Form(""),
    To: str = Form(""),
    NumMedia: str = Form("0"),
) -> str:
    """Twilio sends WhatsApp webhooks as form-encoded POST."""
    log.debug("WhatsApp webhook from %s: %s", From, Body)

    registry = request.app.state.channel_registry
    bridge = registry.get("whatsapp")
    if bridge is None:
        raise HTTPException(status_code=503, detail="WhatsApp bridge not configured")

    # Check if this is an approval reply
    body_upper = Body.strip().upper()
    if body_upper.startswith("APPROVE ") or body_upper.startswith("REJECT "):
        return await _handle_whatsapp_approval(request, Body.strip())

    raw = {"From": From, "Body": Body, "MessageSid": MessageSid, "To": To, "NumMedia": NumMedia}
    channel_message = bridge.normalize_inbound(raw)
    result = await request.app.state.ingress_service.ingest(channel_message)

    # Twilio expects TwiML response (empty is fine for no auto-reply)
    return "<Response></Response>"


async def _handle_whatsapp_approval(request: Request, text: str) -> str:
    """Parse 'APPROVE <id>' or 'REJECT <id>' from WhatsApp replies."""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return "<Response></Response>"

    action, approval_id = parts[0].upper(), parts[1]
    gate = request.app.state.hitl_gate

    if action == "APPROVE":
        gate.resolve_approval(approval_id, approved=True, reason="Approved via WhatsApp")
        log.info("Approval %s approved via WhatsApp", approval_id)
    elif action == "REJECT":
        gate.resolve_approval(approval_id, approved=False, reason="Rejected via WhatsApp")
        log.info("Approval %s rejected via WhatsApp", approval_id)

    return "<Response></Response>"


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

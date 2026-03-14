# Channels

Channels are the messaging app bridges that connect users to NightOwl. Each channel adapts platform-specific webhooks into NightOwl's normalized `ChannelMessage` format and routes outbound agent responses and HITL approval requests back through the platform's API.

## Architecture

```
Platform webhook ──► webhooks router ──► bridge.normalize_inbound() ──► IngressService
                                                                              │
Agent response ◄── bridge.send_message() ◄── ChannelRegistry.send_session_reply()
```

Inbound messages arrive at the centralized webhooks router (`api/routers/webhooks.py`), which looks up the appropriate bridge, normalizes the payload, and forwards to the `IngressService`. Outbound replies flow back through the `ChannelRegistry`, which maps sessions to their originating channel and chat ID.

## Components

### ChannelBridge ABC (`base.py`)

Defines the contract every bridge must implement:

- **`normalize_inbound`** — converts raw platform payload to `ChannelMessage`
- **`send_message`** — sends a text reply to a user
- **`send_approval_request`** — sends an inline HITL approval prompt with approve/reject controls

### ChannelRegistry (`base.py`)

Central registry that tracks registered bridges, last-used channel per user, and session-to-channel routing. The `IngressService` and `HITLGate` both use the registry to route outbound messages to the correct bridge and chat.

### Bridges

- **TelegramBridge** (`telegram.py`) — uses `python-telegram-bot`. Approval requests render as inline keyboard buttons.
- **WhatsAppBridge** (`whatsapp.py`) — uses Twilio WhatsApp Business API. Approvals are text-based ("Reply APPROVE or REJECT").
- **SMSBridge** (`sms.py`) — uses Twilio SMS API. Same text-based approval pattern as WhatsApp.

Telegram is registered automatically in `main.py` when `TELEGRAM_BOT_TOKEN` is set. WhatsApp and SMS require Twilio credentials.

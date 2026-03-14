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
- **`send_approval_request`** — sends an inline HITL approval prompt with approve/reject/redirect controls. Redirect does not carry the replacement instruction inline; it asks the user for a follow-up message.

### ChannelRegistry (`base.py`)

Central registry that tracks registered bridges, last-used channel per user, and session-to-channel routing. The `IngressService` and `HITLGate` both use the registry to route outbound messages to the correct bridge and chat.

### Bridges

- **TelegramBridge** (`telegram.py`) — uses `python-telegram-bot`. Approval requests render as inline keyboard buttons for approve, reject, and redirect. Redirect triggers a follow-up reply prompt in the chat.
- **WhatsAppBridge** (`whatsapp.py`) — uses Twilio WhatsApp Business API. Approvals are text-based ("Reply APPROVE …", "REJECT …", or "REDIRECT …"). After `REDIRECT`, the next user message becomes the new instruction.
- **SMSBridge** (`sms.py`) — uses Twilio SMS API. Same text-based approval pattern as WhatsApp.

Telegram is registered automatically in `main.py` when `TELEGRAM_BOT_TOKEN` is set. WhatsApp and SMS require Twilio credentials.

### Message Formatting (`formatting.py`)

Converts LLM markdown output to each channel's native rich text format:

- **`markdown_to_telegram_html`** — Telegram HTML (`<b>`, `<i>`, `<code>`, `<pre>`, `<a>`)
- **`markdown_to_whatsapp`** — WhatsApp markup (`*bold*`, `_italic_`, `` ```code``` ``)
- **`markdown_to_plaintext`** — clean plain text with Unicode structure (for SMS)

Handles code blocks, headers, bold/italic, strikethrough, links, lists, blockquotes, and horizontal rules.

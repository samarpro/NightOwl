# API

FastAPI routers that expose NightOwl's HTTP and WebSocket interface. All routes live under `/api/v1/`.

## Routers

### Health (`routers/health.py`)

`GET /api/v1/health` — returns `{"status": "ok"}`.

### Ingest (`routers/ingest.py`)

`POST /api/v1/message/ingest` — accepts a `ChannelMessage` body and forwards it to the `IngressService`. Returns the session ID and whether a new session was created. Used by internal services and testing; channel webhooks use the webhooks router instead.

### Approvals (`routers/approvals.py`)

`POST /api/v1/approvals/respond` — accepts an `ApprovalResponse` body and resolves a pending HITL approval via the gate. Used by the dashboard UI.

### Webhooks (`routers/webhooks.py`)

`POST /api/v1/channels/telegram/webhook` — Telegram Bot API webhook endpoint. Validates the secret token header, normalizes the inbound message via the Telegram bridge, and forwards to the `IngressService`. Additional channel webhooks (WhatsApp, SMS) will follow the same pattern.

### WebSocket (`routers/websocket.py`)

`WS /ws` — bidirectional WebSocket. Server pushes `RuntimeEvent` envelopes from the `RuntimeBroadcaster`. Client can send `approval.respond` messages to resolve pending approvals without a separate HTTP call.

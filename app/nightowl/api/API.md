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

`POST /api/v1/channels/telegram/webhook` — Telegram Bot API webhook endpoint. Validates the secret token header, handles two payload types: regular messages (normalized and forwarded to `IngressService`) and callback queries (inline keyboard button presses for HITL approve/reject, resolved directly via the gate). Answers callback queries to clear Telegram's loading spinner.

`POST /api/v1/channels/whatsapp/webhook` — Twilio WhatsApp webhook (form-encoded). Normalizes inbound messages and forwards to `IngressService`. Also handles text-based HITL approval replies ("APPROVE {id}" / "REJECT {id}").

`GET /api/v1/composio/auth/callback` — Composio redirects here when a user completes an OAuth flow. Resolves the pending `AuthWaiter` event so the blocked tool execution can retry.

### Skills (`routers/skills.py`)

CRUD API for skill management:

- `GET /api/v1/skills/` — list all skills (enabled and disabled)
- `GET /api/v1/skills/{name}` — full skill details including body
- `POST /api/v1/skills/upload` — upload a SKILL.md file
- `POST /api/v1/skills/` — create/update from raw content
- `DELETE /api/v1/skills/{name}` — delete skill and its resources
- `PATCH /api/v1/skills/{name}/toggle` — enable or disable

### Observability (`routers/observability.py`)

- `GET /api/v1/observability/intent-graph/{session_id}` — current intent graph
- `GET /api/v1/observability/intent-graphs` — all session graphs
- `GET /api/v1/observability/tokens/{session_id}?last=N` — recent raw token entries
- `POST /api/v1/observability/intent-graph/{session_id}/process` — manually trigger classification

### Shadow (`routers/shadow.py`)

- `POST /api/v1/sessions/{session_id}/shadow` — create a shadow agent for a live session
- `POST /api/v1/shadow/{shadow_id}/message` — chat with the shadow
- `POST /api/v1/shadow/{shadow_id}/correct` — push a correction to the live agent
- `DELETE /api/v1/shadow/{shadow_id}` — destroy a shadow

### WebSocket (`routers/websocket.py`)

`WS /ws` — bidirectional WebSocket. Server pushes `RuntimeEvent` envelopes from the `RuntimeBroadcaster`. Client can send `approval.respond` messages to resolve pending approvals without a separate HTTP call.

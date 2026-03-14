# Webhook Ingress And Channel Signal Implementation Plan

## Purpose

Implement the missing runtime path so that when a user reaches out through a supported channel, NightOwl:

1. accepts the provider webhook
2. verifies and normalizes the inbound payload
3. creates or resumes the correct session
4. runs the agent against the inbound message
5. emits realtime events to the dashboard
6. sends replies and approvals back through the originating channel

This plan is derived from:

- [docs/SPEC.md](/Users/samkanu/Projects/Hack48Winners/docs/SPEC.md)
- [docs/FRONTEND_SPEC.md](/Users/samkanu/Projects/Hack48Winners/docs/FRONTEND_SPEC.md)
- local OpenClaw reference in `/Users/samkanu/Projects/Hack48Winners/openclaw`

## Problem Statement

The current codebase has the beginnings of session orchestration and HITL approvals, but it does not yet have the end-to-end channel ingress system required by the product spec.

What exists today:

- FastAPI app shell in [app/nightowl/main.py](/Users/samkanu/Projects/Hack48Winners/app/nightowl/main.py)
- session lifecycle primitives in [app/nightowl/sessions/manager.py](/Users/samkanu/Projects/Hack48Winners/app/nightowl/sessions/manager.py)
- channel message model in [app/nightowl/models/message.py](/Users/samkanu/Projects/Hack48Winners/app/nightowl/models/message.py)
- HITL gate with channel memory and stubbed channel delivery in [app/nightowl/hitl/gate.py](/Users/samkanu/Projects/Hack48Winners/app/nightowl/hitl/gate.py)

What is missing:

- shared ingest endpoint
- channel bridge routers
- outbound channel delivery adapters
- session lookup for inbound channel identities
- websocket endpoint for realtime events
- approval response path from dashboard and channel callbacks

## Hard Constraints

These are implementation constraints, not suggestions.

### Product constraints

- Telegram is the first real channel bridge for MVP.
- The shared ingest path must be channel-agnostic.
- UI-facing events must come from one typed translation path, not ad hoc payloads.
- Outbound replies must return through the originating channel by default.
- Approval prompts must be deliverable to both the dashboard and the originating channel.

### Architectural constraints

- Keep provider-specific parsing, verification, and outbound API calls inside channel bridge modules.
- Keep session orchestration logic out of FastAPI route handlers.
- Do not let raw webhook payloads leak into session logic or UI events.
- Normalize every inbound provider payload into a shared internal message model before orchestration.
- WebSocket broadcasting must use one normalized event envelope.
- Channel state, session state, approval state, and observability state must remain separate concerns.

### Security constraints

- Verify webhook authenticity before trusting the request body semantics.
- Treat all inbound channel text and metadata as untrusted input.
- Store only the minimum provider identifiers needed for reply routing.
- Never log secrets, full auth headers, or raw provider signatures.
- Preserve room for per-channel allowlist checks before agent execution.

### Delivery constraints

- Build the first vertical slice end-to-end before expanding to more channels.
- Add tests for every boundary: verification, normalization, ingest, session routing, outbound delivery, websocket events.
- Do not block the design on perfect multi-channel abstraction; design for extension without over-generalizing the first implementation.

## Mental Model

Think of the runtime in five layers:

1. `Channel bridge`
   Receives Telegram or future provider webhooks, verifies them, and turns them into a `ChannelMessage`.

2. `Ingress service`
   Accepts normalized channel messages and decides whether to create a session or resume an existing one.

3. `Session runtime`
   Runs the agent, manages child sessions, and produces structured runtime events.

4. `Delivery layer`
   Sends agent replies, approval prompts, and follow-up events back to the correct channel.

5. `Observability layer`
   Broadcasts normalized events to `/ws` so the dashboard can show channel, task, session, and approval state.

### Visual flow

```text
Telegram webhook
    |
    v
[telegram router]
    |
    v
[telegram verifier + normalizer]
    |
    v
ChannelMessage
    |
    v
[shared ingress service]
    |
    +--> resolve session key from channel/sender/thread
    |       |
    |       +--> existing session -> enqueue inbound message
    |       +--> no session -> create main session
    |
    v
[session runner]
    |
    +--> emits runtime events -> [websocket broadcaster]
    |
    +--> produces assistant reply -> [channel delivery adapter]
    |
    +--> requests approval -> [dashboard + channel approval delivery]
```

## Implementation Goals

At completion, the system should support this experience:

1. A Telegram user sends a message to the bot.
2. NightOwl receives the webhook and validates it.
3. The message becomes a normalized `ChannelMessage`.
4. NightOwl creates or resumes a session linked to that Telegram chat.
5. The agent runs and emits structured events.
6. The dashboard updates in realtime through WebSocket.
7. The assistant reply is sent back to Telegram.
8. If the action is high risk, NightOwl pauses and sends an approval prompt both to the web dashboard and Telegram.

## Proposed Directory Additions

This file does not force exact naming, but the final structure should look close to this:

```text
app/nightowl/
  api/
    routers/
      health.py
      ingest.py
      websocket.py
      approvals.py
  channels/
    __init__.py
    types.py
    registry.py
    session_routing.py
    outbound.py
    service.py
    telegram/
      __init__.py
      router.py
      verify.py
      normalize.py
      outbound.py
      schemas.py
      tests/
  events/
    __init__.py
    schemas.py
    broadcaster.py
    translate.py
  ingest/
    __init__.py
    service.py
    tests/
```

## Core Data Contracts

### 1. Normalized inbound message

Current model:

- `ChannelMessage(channel, sender_id, text, thread_id)`

This should be expanded so the runtime has enough routing context without carrying raw provider payloads.

Recommended shape:

```python
class ChannelMessage(BaseModel):
    channel: str
    sender_id: str
    text: str
    thread_id: str | None = None
    chat_id: str | None = None
    message_id: str | None = None
    sender_display_name: str | None = None
    received_at: datetime | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
```

Rules:

- `channel`, `sender_id`, and `text` remain required
- `chat_id` is required for reply routing on messaging channels
- `metadata` may carry safe normalized values only
- raw provider payloads must not be stored here

### 2. Session routing key

Add a simple routing key model:

```python
class ChannelSessionKey(BaseModel):
    channel: str
    sender_id: str
    thread_id: str | None = None
    chat_id: str | None = None
```

Use it to answer:

- should this inbound message resume an existing session?
- where should replies go?

### 3. Normalized event envelope

The frontend spec already calls for normalized realtime events. The backend should standardize on:

```python
class RuntimeEvent(BaseModel):
    event_id: str
    event_type: str
    occurred_at: datetime
    session_id: str | None = None
    channel: str | None = None
    payload: dict[str, Any]
```

Minimum event families for this epic:

- `channel.message_received`
- `channel.reply_queued`
- `channel.reply_sent`
- `channel.reply_failed`
- `session.created`
- `session.resumed`
- `session.updated`
- `agent.response`
- `approval.requested`
- `approval.resolved`
- `approval.timeout`
- `error`

## Implementation Phases

## Phase 1: Shared Ingress Backbone

### Deliverables

- `POST /api/v1/message/ingest`
- ingress service that accepts normalized `ChannelMessage`
- session lookup or creation logic
- event broadcast for inbound message receipt

### Responsibilities

Add an ingress service that does the following:

1. validate normalized message
2. derive channel session key
3. resolve existing session if one is active for that route
4. otherwise create a main session
5. record last known channel target for outbound replies and approvals
6. enqueue the user message for the session runtime
7. emit `channel.message_received` and `session.created` or `session.resumed`

### Code shape

- FastAPI route should be thin
- orchestration goes in `ingest/service.py`
- session route mapping belongs in `channels/session_routing.py`

### Key design decision

The shared ingest endpoint is internal infrastructure. Channel routers should call it as a service function, not necessarily by making an internal HTTP request.

That keeps:

- tests smaller
- control flow cheaper
- route handlers thinner

## Phase 2: Telegram Vertical Slice

### Deliverables

- Telegram webhook router
- Telegram request verification strategy
- Telegram payload normalization
- Telegram outbound text sender

### Responsibilities

Telegram bridge must:

1. receive webhook requests
2. verify secret token if configured
3. reject unsupported update shapes cleanly
4. extract text messages into `ChannelMessage`
5. call shared ingress service
6. return a fast provider-compatible response

### Telegram-specific normalized fields

- `channel = "telegram"`
- `sender_id = from.id`
- `chat_id = chat.id`
- `thread_id = message_thread_id` when present
- `message_id = message.message_id`

### Important behavior

- return quickly from the webhook route
- agent execution may continue asynchronously if necessary
- do not couple Telegram webhook response time to full agent completion

This mirrors the OpenClaw principle that webhook handlers should be transport boundaries, not orchestration engines.

## Phase 3: Outbound Delivery Layer

### Deliverables

- generic outbound delivery interface
- Telegram implementation
- session-to-channel target memory

### Outbound abstraction

Create a small interface, not a framework:

```python
class ChannelOutbound(Protocol):
    async def send_text(self, target: ChannelTarget, text: str) -> DeliveryResult: ...
```

Minimal supporting types:

- `ChannelTarget(channel, chat_id, thread_id, sender_id)`
- `DeliveryResult(provider_message_id, delivered, error)`

### Responsibilities

The delivery layer should:

1. resolve the latest reply target for a session
2. choose the matching outbound adapter by channel
3. send the text
4. emit sent or failed events

### Rules

- the session runtime should not speak Telegram directly
- outbound adapters should know provider APIs, not session logic

## Phase 4: Session Routing And Lifecycle Linkage

### Deliverables

- channel-to-session mapping store
- lifecycle hooks for creating, resuming, and expiring session routes

### Session routing rules

For MVP:

- one active session per `(channel, chat_id, thread_id?)`
- if a new inbound message arrives for an active route, resume that session
- if the prior session is terminal, create a new main session

### Data storage options

Start simple:

- in-memory map for hackathon speed

Design for later:

- persist route mappings in SQLite so webhook restarts do not lose conversations

### Why this matters

Without explicit route-to-session mapping, the system cannot answer the core product question:

`When this channel reaches out, which agent session should receive the signal?`

## Phase 5: WebSocket Realtime Backbone

### Deliverables

- `/ws` endpoint
- event broadcaster service
- typed backend event schema

### Responsibilities

The websocket layer should:

1. accept dashboard connections
2. stream normalized runtime events
3. preserve one event envelope format
4. support approval responses from the dashboard

### Initial client messages

- `approval.respond`

### Initial server messages

- session lifecycle events
- channel lifecycle events
- approval lifecycle events
- agent response events
- error events

### Important rule

Do not broadcast raw dicts from arbitrary modules forever. Introduce one translation point so backend events become stable contracts instead of accidental payloads.

## Phase 6: Approval Round-Trip

### Deliverables

- complete `HITLGate` channel delivery path
- dashboard approval response route or websocket handling
- optional Telegram approval callback handling

### Responsibilities

When a risky action requires approval:

1. create approval request
2. emit `approval.requested`
3. send channel approval message using the last known target
4. accept approval resolution from dashboard
5. later accept approval resolution from channel callback interactions if implemented
6. emit `approval.resolved` or `approval.timeout`

### MVP guidance

Dashboard approval is mandatory.

Telegram approval callback is valuable, but if time is limited:

- send a plain Telegram approval notice first
- finish dashboard response flow before implementing Telegram inline button callbacks

## Phase 7: Additional Channels

After Telegram is stable, add more bridges by reusing the same architecture:

- WhatsApp
- Twilio SMS
- Web UI direct channel

Each new bridge should only implement:

- verification
- normalization
- outbound delivery
- optional channel-specific approval callbacks

It should not reimplement ingest or session orchestration.

## Recommended Event Mapping

To help the frontend visualize system behavior, use event payloads that directly answer operator questions.

### `channel.message_received`

```json
{
  "channel": "telegram",
  "chatId": "12345",
  "senderId": "67890",
  "textPreview": "Plan a night out for Saturday",
  "messageId": "99"
}
```

### `session.created`

```json
{
  "sessionId": "session:abc123",
  "role": "main",
  "task": "Plan a night out for Saturday",
  "channel": "telegram"
}
```

### `session.resumed`

```json
{
  "sessionId": "session:abc123",
  "channel": "telegram",
  "reason": "inbound_channel_message"
}
```

### `channel.reply_sent`

```json
{
  "sessionId": "session:abc123",
  "channel": "telegram",
  "chatId": "12345",
  "textPreview": "I found five restaurant options near the CBD"
}
```

### `approval.requested`

```json
{
  "approvalId": "approval:xyz789",
  "sessionId": "session:abc123",
  "channel": "telegram",
  "toolName": "make_reservation",
  "riskLevel": "high"
}
```

## Testing Plan

## Unit tests

Add tests for:

- Telegram payload normalization
- Telegram secret verification
- session routing key generation
- route-to-session lookup
- outbound adapter success and failure behavior
- event translation to websocket envelope

## Integration tests

Add tests for:

- `POST /api/v1/message/ingest`
- Telegram webhook -> normalized message -> session creation
- inbound message on existing route -> session resume
- risky tool call -> approval requested -> dashboard resolution
- assistant reply -> outbound adapter invoked

## Contract tests

Add tests that assert the websocket event payloads are stable and parseable.

This matters because the frontend spec assumes typed event translation and reconnect-safe behavior.

## Suggested Build Order

Implement in this order:

1. normalized event envelope
2. shared ingress service
3. session routing store
4. ingest API route
5. Telegram normalizer and router
6. Telegram outbound sender
7. websocket route
8. HITL dashboard resolution path
9. Telegram approval callback support
10. second channel bridge

This order delivers a visible, testable vertical slice early.

## Definition Of Done

This epic is complete when all of the following are true:

- a Telegram message can start a new NightOwl session
- a follow-up Telegram message can resume the correct active session
- the dashboard receives realtime websocket events for inbound messages, session state, replies, and approvals
- assistant replies are sent back to Telegram
- high-risk actions pause and create approval requests visible in the dashboard
- approval resolution unblocks execution
- backend tests cover normalization, routing, ingest, outbound delivery, and approval flow

## Non-Goals For This Epic

Avoid pulling these into the first implementation unless they are required to unblock the vertical slice:

- durable multi-tenant route persistence
- every OpenClaw channel
- advanced delivery retries and dead-letter queues
- rich media support
- editing or deleting sent provider messages
- complex rate limiting

## Reader Notes

If you are implementing from this plan, keep this picture in mind:

- `channels/*` is the transport edge
- `ingest/*` is the system entry point
- `sessions/*` is the orchestration core
- `events/*` is the observability contract
- `frontend` should only ever see stable event shapes

That separation is what makes the code understandable. When a new channel is added later, the team should be able to point to one small transport module and say:

`This adapter turns that channel's signal into NightOwl's shared runtime flow.`

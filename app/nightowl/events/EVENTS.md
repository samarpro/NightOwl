# Events

The event system connects NightOwl's internal runtime to external consumers (dashboard WebSocket, CLI, activity feeds). It has two layers: a Redis pub/sub bus for distributed consumers, and an in-memory broadcaster for WebSocket delivery.

## Components

### EventBus (`bus.py`)

Redis pub/sub on a single `nightowl:events` channel. Publish from anywhere (session manager, HITL gate, ingress service), subscribe from anywhere. Multiple independent consumers — no single-consumer contention. Used by the CLI for approval listening.

### RuntimeBroadcaster (`broadcaster.py`)

In-memory fan-out for WebSocket subscribers. The `SessionManager` and other components publish raw internal events to the broadcaster. Before delivery, each event passes through the translator to produce a typed `RuntimeEvent` envelope. Events that don't map to a known type are silently dropped.

This is the event bus used by the FastAPI server (`main.py` wires it as the manager's event bus). The CLI uses `EventBus` directly instead.

### RuntimeEvent schema (`schemas.py`)

Typed Pydantic model for WebSocket delivery: `event_id`, `event_type`, `occurred_at`, optional `session_id` and `channel`, and a `payload` dict. This is the contract between backend and frontend.

### Translator (`translate.py`)

Maps raw internal event dicts (e.g., `session:created`, `approval:required`, `channel:message_received`) into `RuntimeEvent` envelopes with frontend-friendly field names (camelCase payloads, truncated text previews). Unrecognized event types return `None` and are dropped.

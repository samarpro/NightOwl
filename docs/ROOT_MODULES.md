# Root Modules

Top-level files in `app/nightowl/` that wire the application together.

## `main.py` — FastAPI Entrypoint

Creates the FastAPI app with a lifespan context manager. On startup: initializes the database, creates a `SessionManager`, and sets up a broadcast queue. On shutdown: closes the database connection. Serves the health endpoint at `/api/v1/health`.

## `cli.py` — Interactive Chat

A terminal-based REPL for development. Wires up the `SessionManager`, `EventBus`, and `HITLGate`, then runs `run_interactive` from the session runner. Approval requests appear inline — the CLI prompts for y/n and resolves via the gate.

Run it with `pdm run chat` from the `app/` directory.

## `config.py` — Configuration

All configuration is via `pydantic-settings`, loaded from environment variables or `.env`. Key settings: Bedrock region/model, Composio API key, Redis URL, database URL, session spawn limits (max depth, max children), and HITL timeout.

## `events.py` — Event Bus

Redis pub/sub event bus on a single `nightowl:events` channel. All system events (session lifecycle, approvals, node progress) flow through it. Multiple consumers can subscribe independently — the dashboard WebSocket, CLI approval listener, and activity feed all read from the same channel with optional type filtering.

## `db.py` — Database

PostgreSQL via SQLAlchemy async. Defines three tables: `sessions`, `messages`, and `approvals`. Schema is auto-created on startup via `init_db()`. The session factory is shared through FastAPI's lifespan state.

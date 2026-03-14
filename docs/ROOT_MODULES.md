# Root Modules

Top-level files in `app/nightowl/` that wire the application together.

## `main.py` — FastAPI Entrypoint

Factory function `create_app()` builds the FastAPI application with all routers (health, ingest, approvals, webhooks, WebSocket). The lifespan context manager initializes: database, `RuntimeBroadcaster`, `SessionManager`, `ChannelRegistry` (auto-registers Telegram if token is set), `HITLGate`, and `IngressService`. All are stored on `app.state` for router access.

## `cli.py` — Interactive Chat

A terminal-based REPL for development. Wires up the `SessionManager`, `EventBus`, and `HITLGate`, then runs `run_interactive` from the session runner. Approval requests appear inline — the CLI prompts for y/n and resolves via the gate.

Run it with `pdm run chat` from the `app/` directory.

## `config.py` — Configuration

All configuration is via `pydantic-settings`, loaded from environment variables or `.env`. Key settings: Bedrock region/model, Composio API key, channel tokens (Telegram bot token + webhook secret, Twilio credentials), Redis URL, database URL, session spawn limits (max depth, max children), and HITL timeout.

## `db.py` — Database

PostgreSQL via SQLAlchemy async. Defines three tables: `sessions`, `messages`, and `approvals`. Schema is auto-created on startup via `init_db()`. The session factory is shared through FastAPI's lifespan state.

# Root Modules

Top-level files and packages in `app/nightowl/` that wire the application together.

## `main.py` — FastAPI Entrypoint

Factory function `create_app()` builds the FastAPI application with all routers (health, ingest, approvals, skills, webhooks, WebSocket). The lifespan context manager initializes: database, `SessionStore`, `SkillStore`, `RuntimeBroadcaster`, `SessionManager`, `ChannelRegistry`, `HITLGate`, `DockerSandboxManager`, and `IngressService`. On startup, loads built-in skills from `skills_library/` and attempts to resume an active session from the database. On shutdown, cleans up all sandbox containers. All services are stored on `app.state` for router access.

## `cli.py` — Interactive Chat

A terminal-based REPL for development. Wires up the `SessionManager`, `EventBus`, and `HITLGate`, then runs `run_interactive` from the session runner. Approval requests appear inline — the CLI prompts for y/n and resolves via the gate.

Run it with `pdm run chat` from the `app/` directory.

## `config.py` — Configuration

All configuration is via `pydantic-settings`, loaded from environment variables or `.env`. Key settings: Bedrock region/model, Composio API key + user ID, channel tokens (Telegram bot token + webhook secret, Twilio credentials), Redis URL, database URL, session spawn limits (max depth, max children), HITL timeout, and `public_url` (needed for OAuth callbacks when behind a tunnel like ngrok).

## `db/` — Database

Refactored from a single `db.py` to a package. PostgreSQL via SQLAlchemy async with Alembic for schema migrations. Models are split one-per-file under `db/models/`: `SessionRow`, `ChatMessageRow`, `MessageRow`, `ApprovalRow`, `SkillRow`, `SkillResourceRow`. The package `__init__.py` re-exports all models and provides `init_db()` / `close_db()`.

Schema is managed by Alembic — run `pdm run migrate` to apply. The auto-create-all pattern has been replaced by migrations.

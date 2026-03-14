# NightOwl

NightOwl is [OpenClaw](https://github.com/openclaw/openclaw) made safe, observable, and accessible to non-technical users. It keeps OpenClaw's parallel agent swarm model — where the main agent spawns independent child sessions that run concurrently and push results back — but wraps it in human-in-the-loop approvals, real-time observability, and managed infrastructure.

Users interact through messaging apps (Telegram, WhatsApp, SMS). Agents coordinate via a session manager, execute tools through Composio's MCP gateway, and run sandboxed CLI/browser/computer-use tasks in ephemeral Docker containers. A web dashboard shows the live session tree, agent activity, and pending approval requests.

## Architecture

```
Messaging Apps (Telegram, WhatsApp, SMS)
        │  webhooks
        ▼
   FastAPI Gateway
        │
        ├── Session Manager ──► Agent Sessions (parallel, depth-limited)
        │       │                    │
        │       │                    ├── Composio MCP tools (calendar, email, search)
        │       │                    ├── Sandbox containers (bash, browser, computer use)
        │       │                    └── HITL gate (blocks high-risk actions for approval)
        │       │
        │       └── Event Bus (Redis) ──► Dashboard (WebSocket)
        │
        └── AWS Bedrock (Claude inference + Guardrails)
```

## Prerequisites

- Python 3.14
- [PDM](https://pdm-project.org/) package manager
- Docker (for Redis, and later for sandbox containers)
- AWS credentials configured for Bedrock access
- A Composio API key (for MCP tool integrations)

## Setup

```sh
# Start Redis
docker compose up -d

# Install dependencies
cd app
pdm install

# Configure environment
cp .env.example .env   # then fill in your keys
```

The app reads all configuration from environment variables or a `.env` file in `app/`. See `nightowl/config.py` for the full list — the essentials are:

| Variable | Purpose |
|----------|---------|
| `BEDROCK_REGION` / `BEDROCK_MODEL` | AWS Bedrock LLM endpoint |
| `COMPOSIO_API_KEY` | Composio MCP gateway auth |
| `REDIS_URL` | Event bus (defaults to `redis://localhost:6379`) |
| `DATABASE_URL` | PostgreSQL connection string |

## Running

**CLI mode** (single interactive session, useful for development):

```sh
cd app
pdm run chat
```

**API server** (full gateway with WebSocket support):

```sh
cd app
uvicorn nightowl.main:app --reload
```

## Testing

```sh
cd app
pdm run pytest
```

## Project Structure

```
app/nightowl/
├── sessions/       # Session manager, agent runner, spawn/list/send tools
├── hitl/           # Risk classifier and approval gate
├── composio_tools/ # Composio MCP tool router and meta-tools
├── channels/       # Channel bridge abstraction (Telegram, etc.)
├── models/         # Pydantic data models
├── config.py       # pydantic-settings configuration
├── db.py           # Database initialization
├── events.py       # Redis-backed event bus
├── cli.py          # Interactive CLI chat
└── main.py         # FastAPI app entrypoint
```

## Documentation

- `docs/SPEC.md` — full technical specification and design decisions
- `docs/DOCUMENTATION.md` — documentation standards for this project

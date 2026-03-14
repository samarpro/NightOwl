# NightOwl Technical Specification

> Version 0.2.0 — Hackathon MVP

## What is NightOwl?

NightOwl is [OpenClaw](https://github.com/openclaw/openclaw), but safe, observable, and built for non-technical users.

OpenClaw is a powerful personal AI assistant that talks to you on your messaging apps (WhatsApp, Telegram, iMessage, etc.) and coordinates your life via MCP integrations. But it requires CLI setup, has no guardrails, and gives zero visibility into what the agent is doing.

NightOwl wraps the same concept with:

- **One-click install** — no terminal, no `npm install`, no config files
- **Observability dashboard** — see what the agent is thinking, what tools it's calling, what it sent
- **Human-in-the-loop approvals** — high-risk actions (sending messages, making reservations) require explicit user approval before execution
- **AWS Bedrock Guardrails** — prompt injection detection, PII filtering, and content moderation handled at the infrastructure layer, not in our code

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    USER'S MESSAGING APPS                      │
│       WhatsApp  |  Telegram  |  iMessage  |  SMS             │
└──────────────────────────────────────────────────────────────┘
                              |
                              v  (webhooks / bridges)
┌──────────────────────────────────────────────────────────────┐
│                        NIGHTOWL CORE                          │
│                                                               │
│   FastAPI Gateway                                             │
│     - Message ingress from channel bridges                    │
│     - WebSocket to dashboard for real-time observability      │
│     - REST endpoints for config and health                    │
│                              |                                │
│                              v                                │
│   Pydantic AI Agent                                           │
│     - Conversation state management                           │
│     - Task planning and tool orchestration                    │
│     - HITL checkpoints for high-risk actions                  │
│     - MCP servers wired directly via pydantic-ai              │
│                              |                                │
│                              v                                │
│   AWS Bedrock                                                 │
│     - LLM inference (Claude Sonnet 4)                         │
│     - Guardrails (prompt injection, PII, content filtering)   │
│                                                               │
└──────────────────────────────────────────────────────────────┘
          |                                        |
          v                                        v
┌──────────────────┐                ┌─────────────────────────┐
│   Web Dashboard   │                │   External MCP Servers  │
│   - Activity feed │                │   - Google Calendar     │
│   - Approval queue│                │   - Gmail               │
│   - Settings      │                │   - Asana               │
└──────────────────┘                │   - OpenTable / Resy    │
                                    │   - Web search          │
                                    └─────────────────────────┘
```

## Key Design Decisions

### Safety is Bedrock's job, not ours

AWS Bedrock Guardrails provides prompt injection detection, PII filtering, and content moderation as a managed service. We configure guardrails on the Bedrock side and let every LLM call pass through them. We do not implement any prompt injection detection, PII regex, or content filtering in our codebase.

What *is* our job: **action risk classification and HITL gating**. Before the agent executes a tool call, we classify the risk and gate high-risk actions behind user approval. This is application logic, not security infrastructure.

### MCP servers wire directly into the Pydantic AI agent

Following the pattern from the Atlastix agent factory: MCP servers connect via `MCPServerStreamableHTTP` and are passed directly to the Pydantic AI `Agent` constructor via `mcp_servers=`. No custom proxy layer needed — Pydantic AI handles tool discovery and invocation natively.

### Web dashboard, not Electron

The dashboard is a standard React web app served by the FastAPI backend. Electron is just a wrapper around a web view anyway. For the hackathon, a browser tab is fine. Electron packaging can come later if needed.

### Channel bridges adapt from OpenClaw

OpenClaw already has battle-tested channel integrations (WhatsApp, Telegram, iMessage, etc.) under `extensions/`. These are TypeScript, so we adapt the protocol/webhook handling to our Python gateway rather than forking the code directly. For MVP, Telegram is the easiest channel to get running.

## Technology Stack

### Backend (Python)

| Component | Technology | Why |
|-----------|------------|-----|
| Web framework | FastAPI | Async, WebSocket support, OpenAPI docs |
| Agent framework | Pydantic AI | Type-safe, MCP-native, streaming, tool calling |
| LLM + guardrails | AWS Bedrock (Claude Sonnet 4) | Managed inference + guardrails in one service |
| Database | SQLite | Conversation history, audit log. Sufficient for single-user MVP |
| Package manager | PDM | Already set up in `api/pyproject.toml` |

### Frontend (Web Dashboard)

| Component | Technology | Why |
|-----------|------------|-----|
| Framework | React | Component model, ecosystem |
| Styling | Tailwind CSS | Fast iteration |
| Components | shadcn/ui | Accessible, not a black box |
| Real-time | WebSocket | Live activity feed and approval notifications |

## Components

### 1. FastAPI Gateway

Accepts messages from channel bridges, routes them through the agent, and broadcasts events to the dashboard via WebSocket.

**REST endpoints:**
- `POST /api/v1/message/ingest` — channel bridge sends incoming user message
- `GET /api/v1/health` — health check
- `GET /api/v1/config` — current configuration
- `PUT /api/v1/config` — update configuration

**WebSocket `/ws`:**
- Server pushes: `agent:thinking`, `agent:tool_call`, `agent:response`, `approval:required`, `approval:timeout`, `error`
- Client sends: `approval:respond`, `config:update`

### 2. Pydantic AI Agent

The core agent that receives user messages, plans tasks, calls tools via MCP, and triggers HITL checkpoints.

Key points:
- Uses `instructions=` (not `system_prompt=`) per Pydantic AI best practice — models respond better to instructions
- MCP servers passed directly to Agent constructor
- Agent deps carry conversation state (user ID, channel, timezone, preferences)
- Tools that involve external communication or financial commitment gate behind HITL approval

**Risk levels for HITL gating:**

| Level | HITL? | Examples |
|-------|-------|---------|
| `low` | No | Reading calendar, web search, searching contacts |
| `medium` | No | Creating calendar event, updating a task |
| `high` | Yes | Sending messages, making reservations |
| `critical` | Yes + confirm | Payments, cancellations, deletions |

### 3. MCP Integrations

MCP servers connect to the agent via `MCPServerStreamableHTTP` from `pydantic-ai`. OAuth tokens are managed per-user.

Target integrations for MVP demo:
- Google Calendar (read/write events)
- Gmail (read/send)
- Web search (Tavily or similar)

Stretch:
- OpenTable / Resy (restaurant reservations)
- Asana (task management)

### 4. Web Dashboard

Single-page React app served by FastAPI. Connects to the gateway via WebSocket.

**Views:**
- **Activity feed** — real-time stream of agent thinking, tool calls, responses
- **Approval queue** — pending HITL approval requests with approve/reject buttons and countdown timer
- **Settings** — channel configuration, MCP server connections

### 5. Channel Bridges

For MVP, Telegram is the primary channel (Bot API, easy to set up, reliable).

Each bridge is a FastAPI router that:
1. Receives incoming webhooks from the messaging platform
2. Normalises the message format
3. Forwards to the gateway's ingest endpoint
4. Receives outbound messages from the agent and sends via platform API

## Demo Scenario: "Plan a night out"

User sends via Telegram: *"Plan a night out for 4 people this Saturday near the CBD"*

1. Agent searches calendar for conflicts (low risk, no approval needed)
2. Agent searches restaurants with availability (low risk)
3. Agent presents options to user via Telegram
4. User picks a restaurant
5. Agent requests approval to make reservation (high risk -> HITL)
6. Dashboard shows approval card with restaurant, date, time, party size
7. User approves
8. Agent makes reservation, confirms back via Telegram

## Open Questions

1. How do we handle OAuth flows for MCP servers from a one-click install? The dashboard needs to walk users through connecting their Google account, etc.
2. Should the agent maintain conversation history in the DB or just in-memory per session?
3. What's the right UX for approval on mobile when the user is away from the dashboard? Push notifications?

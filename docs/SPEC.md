# NightOwl Technical Specification

> Version 0.4.0 — Hackathon MVP

## What is NightOwl?

NightOwl is [OpenClaw](https://github.com/openclaw/openclaw), but safe, observable, and built for non-technical users.

OpenClaw is a powerful personal AI assistant that talks to you on your messaging apps (WhatsApp, Telegram, iMessage, etc.) and coordinates your life via MCP integrations and CLI tools. It can spawn parallel agent swarms, run shell commands, and automate complex workflows. But it requires CLI setup, has no guardrails, and gives zero visibility into what the agent is doing.

NightOwl bridges the gap between OpenClaw's raw capability and enterprise-grade safety:

- **One-click install** — no terminal, no `npm install`, no config files
- **Observability dashboard** — see what every agent in the swarm is doing in real-time
- **Human-in-the-loop approvals** — high-risk actions require explicit user approval before execution
- **AWS Bedrock Guardrails** — prompt injection detection, PII filtering, and content moderation at the infrastructure layer
- **Composio for MCP auth** — OAuth, API keys, and token refresh managed by Composio's MCP gateway
- **Containerised execution** — computer use, browser use, and CLI tools run in sandboxed containers

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
│     - Session manager (agent lifecycle, spawn, completion)    │
│     - WebSocket to dashboard for real-time observability      │
│                              |                                │
│                              v                                │
│   Agent Sessions (parallel, independent)                      │
│     ┌─────────┐  ┌─────────┐  ┌─────────┐                   │
│     │ Main    │  │ Child A │  │ Child B │  ...               │
│     │ Agent   │─>│ (calendar│  │ (browser│                   │
│     │         │  │  search) │  │  task)  │                   │
│     └─────────┘  └────┬────┘  └────┬────┘                   │
│          ^             |            |                          │
│          └─────────────┴────────────┘                         │
│            completion events pushed back                      │
│                                                               │
│   Sandbox Containers (per-session, ephemeral)                 │
│     - CLI / bash tools                                        │
│     - Browser (Playwright)                                    │
│     - Computer use (screen + mouse)                           │
│                                                               │
│   AWS Bedrock                                                 │
│     - LLM inference (Claude Sonnet 4)                         │
│     - Guardrails (prompt injection, PII, content filtering)   │
│                                                               │
└──────────────────────────────────────────────────────────────┘
       |                  |                        |
       v                  v                        v
┌────────────┐   ┌──────────────┐   ┌─────────────────────────┐
│  Dashboard  │   │   Composio    │   │   External MCP Servers  │
│  - Activity │   │   MCP Gateway │   │   - Google Calendar     │
│  - Approvals│   │   - OAuth mgmt│   │   - Gmail               │
│  - Sessions │   │   - Token     │   │   - Asana               │
│  - Settings │   │     refresh   │   │   - OpenTable / Resy    │
└────────────┘   │   - Tool      │   │   - Web search          │
                  │     routing   │   └─────────────────────────┘
                  └──────────────┘
```

## Key Design Decisions

### Parallel agent sessions, not sub-agents-as-tools

OpenClaw's most powerful feature is its agent swarm model. The main agent spawns child agents as **independent sessions** that run in parallel. Children push completion events back to the parent when done — the parent does NOT poll or block waiting.

This is fundamentally different from Pydantic AI's sub-agent-as-tool pattern (where the parent blocks until the child returns). OpenClaw's approach lets the main agent:
- Spawn multiple children simultaneously for different parts of a task
- Continue thinking/planning while children work
- Receive results asynchronously and synthesise them
- Handle depth limits (main -> orchestrator -> leaf) to prevent runaway spawning

We model this via the gateway's session manager. Each agent session (parent or child) is a separate Pydantic AI agent run, coordinated by the gateway. The gateway handles:
- Session creation and lifecycle (spawn, run, complete, cleanup)
- Routing completion events from children back to parent sessions
- Depth tracking and spawn limits (configurable max depth, max children per agent)
- Sandbox inheritance (sandboxed parents can only spawn sandboxed children)

### Safety is Bedrock's job, not ours

AWS Bedrock Guardrails provides prompt injection detection, PII filtering, and content moderation as a managed service. We configure guardrails on the Bedrock side and let every LLM call pass through them. We do not implement any prompt injection detection, PII regex, or content filtering in our codebase.

What *is* our job: **action risk classification and HITL gating**. Before the agent executes a tool call, we classify the risk and gate high-risk actions behind user approval.

### Composio handles MCP authentication

[Composio's MCP Gateway](https://composio.dev/mcp-gateway) manages OAuth flows, API key storage, token refresh, and scopes for all third-party integrations. This solves the "how do non-technical users connect their Google account" problem — Composio provides hosted auth flows we can redirect to from the dashboard.

The Composio Tool Router gives us a single MCP endpoint that dynamically discovers and serves tools from connected apps. We don't maintain per-service MCP connection logic or OAuth token management ourselves.

### Containerised computer use and CLI tools

A huge part of what makes OpenClaw useful is CLI tool access — running shell commands, automating workflows, scripting. NightOwl preserves this capability but runs it in sandboxed Docker containers so the agent can't damage the host system.

Container capabilities:
- **Bash/CLI** — run arbitrary shell commands, install packages, run scripts
- **Browser use** — headless browser via Playwright or similar for web automation
- **Computer use** — screen interaction (Claude's computer use API) for GUI automation

Containers are ephemeral (spun up per session, torn down after), network-isolated by default, and can be granted specific host mounts or network access via HITL approval. This gives the agent real power while keeping the user safe.

### MCP servers wire directly into Pydantic AI agents

MCP servers connect via `MCPServerStreamableHTTP` and are passed directly to the Pydantic AI `Agent` constructor via `mcp_servers=`. Composio provides the authenticated MCP endpoints; Pydantic AI handles tool discovery and invocation natively. Each agent session can have a different set of MCP servers scoped to its task.

### Web dashboard, not Electron

The dashboard is a standard React web app served by the FastAPI backend. For the hackathon, a browser tab is fine. Electron packaging can come later if needed.

### Channel bridges adapt from OpenClaw

OpenClaw has battle-tested channel integrations under `extensions/`. These are TypeScript, so we adapt the protocol/webhook handling to our Python gateway. For MVP, Telegram is the easiest channel to get running.

## Technology Stack

### Backend (Python)

| Component | Technology | Why |
|-----------|------------|-----|
| Web framework | FastAPI | Async, WebSocket support, OpenAPI docs |
| Agent framework | Pydantic AI | Type-safe, MCP-native, streaming, tool calling |
| LLM + guardrails | AWS Bedrock (Claude Sonnet 4) | Managed inference + guardrails in one service |
| MCP auth | Composio MCP Gateway | Managed OAuth, token refresh, tool routing |
| Container runtime | Docker | Sandboxed execution for computer use, browser, CLI |
| Database | SQLite | Conversation history, session state, audit log |
| Package manager | PDM | Already set up in `api/pyproject.toml` |

### Frontend (Web Dashboard)

| Component | Technology | Why |
|-----------|------------|-----|
| Framework | React | Component model, ecosystem |
| Styling | Tailwind CSS | Fast iteration |
| Components | shadcn/ui | Accessible, not a black box |
| Real-time | WebSocket | Live activity feed and approval notifications |

## Components

### 1. FastAPI Gateway + Session Manager

The gateway accepts messages, manages agent session lifecycles, and broadcasts events to the dashboard.

**Session manager responsibilities:**
- Create and track agent sessions (parent and child)
- Route `sessions_spawn` tool calls to create new child sessions
- Push completion events from child sessions back to parent sessions as messages
- Enforce spawn depth limits and max children per session
- Track sandbox inheritance (sandboxed parent -> sandboxed children only)
- Clean up completed sessions (ephemeral by default, persistent if thread-bound)

**REST endpoints:**
- `POST /api/v1/message/ingest` — channel bridge sends incoming user message
- `GET /api/v1/health` — health check
- `GET /api/v1/sessions` — list active sessions and their state
- `GET /api/v1/config` — current configuration
- `PUT /api/v1/config` — update configuration

**WebSocket `/ws`:**
- Server pushes: `agent:thinking`, `agent:tool_call`, `agent:response`, `agent:spawn`, `agent:complete`, `approval:required`, `approval:timeout`, `error`
- Client sends: `approval:respond`, `config:update`

### 2. Agent Sessions

Each agent session is an independent Pydantic AI agent run. The main session is created when a user message arrives. It can spawn child sessions that run in parallel.

**Session roles** (following OpenClaw's depth model):
- **Main** (depth 0) — the entry point agent. Can spawn children and orchestrate.
- **Orchestrator** (depth 1 to max-1) — spawned child that can itself spawn further children.
- **Leaf** (depth = max) — cannot spawn further children. Must do its work directly.

**Agent tools available to all sessions:**
- `sessions_spawn` — spawn a child agent session with a task description, optional model override, optional sandbox mode. Returns immediately with child session key. Completion arrives as a pushed message.
- `sessions_list` — list active child sessions and their status
- `sessions_send` — send a message to a running child session (steering)

**Agent tools for containerised execution:**
- `bash_exec` — run a shell command in the session's sandbox container
- `browser_navigate` / `browser_interact` — headless browser actions
- `computer_use` — screen capture + mouse/keyboard via Claude's computer use API

**Agent tools for communication:**
- All Composio MCP tools (calendar, email, etc.) — available based on which services the user has connected

**Key behaviours (mirroring OpenClaw):**
- After spawning children, the parent does NOT poll. It waits for completion events to arrive as user messages.
- The parent tracks expected child session keys and only sends its final answer after ALL expected completions arrive.
- Each session gets its own instructions scoped to its task. Child sessions receive: the task description, their depth/role, and context about who spawned them.

### 3. Sandbox Containers

Docker containers for agent execution of CLI, browser, and computer use tasks. Each agent session can optionally have its own container.

**Container types:**
- **CLI sandbox** — bash shell with common tools. Agent can run commands, install packages, write/execute scripts
- **Browser sandbox** — headless Chromium via Playwright. Agent can navigate, fill forms, scrape, automate web workflows
- **Computer use sandbox** — full desktop environment exposed via Claude's computer use API (screen capture + mouse/keyboard input)

**Security model:**
- Containers are ephemeral — created per session, destroyed after
- No host filesystem access by default (explicit mounts via HITL approval)
- No network access by default (explicit grant via HITL approval)
- Resource limits (CPU, memory, time) to prevent runaway processes
- Sandbox inheritance: if a parent session is sandboxed, children must also be sandboxed

### 4. HITL Approval System

Before executing high-risk tool calls, the agent sends an approval request through the gateway to the dashboard. The agent pauses until the user approves or rejects (or timeout).

**Risk levels:**

| Level | HITL? | Examples |
|-------|-------|---------|
| `low` | No | Reading calendar, web search, listing files |
| `medium` | No | Creating calendar event, updating a task |
| `high` | Yes | Sending messages, making reservations, running CLI commands, granting network access |
| `critical` | Yes + confirm | Payments, cancellations, deleting data |

### 5. MCP Integrations via Composio

Composio's MCP Gateway is the single point of authentication for all third-party services. The dashboard walks users through connecting accounts via Composio's hosted OAuth flows.

Target integrations for MVP demo:
- Google Calendar (read/write events)
- Gmail (read/send)
- Web search (Tavily or similar)

Stretch:
- OpenTable / Resy (restaurant reservations)
- Asana (task management)

### 6. Web Dashboard

Single-page React app served by FastAPI. Connects to the gateway via WebSocket.

**Views:**
- **Session tree** — visual tree of active agent sessions (parent -> children), their status, role, and depth. Click into any session to see its activity.
- **Activity feed** — real-time stream of agent thinking, tool calls, spawns, completions, and container output for the selected session
- **Approval queue** — pending HITL approval requests with approve/reject buttons and countdown timer
- **Connections** — Composio-powered OAuth flows for connecting Google, Asana, etc.
- **Settings** — channel configuration, container policies, spawn limits

### 7. Channel Bridges

For MVP, Telegram is the primary channel (Bot API, easy to set up, reliable).

Each bridge is a FastAPI router that:
1. Receives incoming webhooks from the messaging platform
2. Normalises the message format
3. Forwards to the gateway's ingest endpoint
4. Receives outbound messages from the agent and sends via platform API

## Demo Scenario: "Plan a night out"

User sends via Telegram: *"Plan a night out for 4 people this Saturday near the CBD"*

1. Main agent spawns two children in parallel:
   - Child A: check calendar for conflicts (Google Calendar MCP)
   - Child B: search restaurants with availability (web search)
2. Both children run simultaneously. Dashboard shows session tree with both active.
3. Child A completes: "Saturday evening is free"
4. Child B completes: "Found 5 restaurants with availability"
5. Main agent synthesises results, presents options to user via Telegram
6. User picks a restaurant
7. Main agent requests HITL approval to make reservation (high risk)
8. Dashboard shows approval card with restaurant, date, time, party size
9. User approves
10. Main agent spawns Child C to make the reservation, confirms back via Telegram

## Demo Scenario: "Automate this workflow"

User sends via Telegram: *"Download my bank statement from ANZ and categorise the transactions into a spreadsheet"*

1. Main agent requests HITL approval for browser + network access (high risk)
2. User approves via dashboard
3. Main agent spawns Child A (browser sandbox) to download bank statement
4. Dashboard shows live browser activity feed
5. Child A completes with downloaded CSV
6. Main agent spawns Child B (CLI sandbox) to parse and categorise into spreadsheet
7. Child B completes with spreadsheet file
8. Main agent sends file back via Telegram

## Open Questions

1. What's the right UX for approval on mobile when the user is away from the dashboard? Push notifications?
2. How do we handle long-running container tasks? Stream output to dashboard? Timeout policies?
3. Should container images be pre-built (fast start) or built on-demand (more flexible)?
4. How much of OpenClaw's session persistence model do we need for MVP? Ephemeral-only might be sufficient.

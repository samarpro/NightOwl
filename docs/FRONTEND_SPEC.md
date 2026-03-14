# NightOwl Frontend Product Specification

> Version 0.1.0  
> Scope: Web application UI for a secure, human-in-the-loop OpenClaw-style assistant

## 1. Product Framing

NightOwl is a control tower for a multi-agent assistant that can operate through messaging channels like WhatsApp and Telegram, run tools, ask for permission before risky actions, persist memory, and expose everything to the user in a trustworthy interface.

The UI is not a secondary admin panel. It is the primary trust surface of the product. It must make autonomous behavior legible, interruptible, steerable, and safe.

### Core product promise

- Control the assistant from messaging apps, especially WhatsApp, with web UI parity.
- See what the system is doing in real time through a WebSocket-backed dashboard.
- Review and approve privileged or escalated actions before they execute.
- Inspect agent memory, child agents, tool usage, and intent-level reasoning structure.
- Configure channels, skills, and policies with near one-click setup.

### Product posture

- More secure than OpenClaw
- More observable than OpenClaw
- Easier to configure than OpenClaw
- More collaborative between human and agent than OpenClaw

## 2. UI Vision

The UI should feel like an "air traffic control" layer for autonomous work:

- left rail for navigation and global status
- center workspace for task, session, and graph inspection
- right rail for live detail, approvals, and steering actions

The visual language should communicate live systems behavior:

- active states feel animated and responsive
- risky states are unmistakable
- system health is glanceable
- agent hierarchies and intentions are explorable, not hidden in logs

## 3. Primary User Goals

The UI must help users do these jobs well:

1. Understand what task is running, who is working on it, and whether it is safe.
2. Approve or reject risky actions without reading raw logs.
3. Inspect the active channels and know which communication surfaces are healthy or failing.
4. Redirect a specific agent or sub-agent without stopping the whole task.
5. Understand action history grouped by intention, not just timestamp order.
6. Import and manage `SKILLS.md` capabilities.
7. Set up the product quickly without terminal-heavy configuration.
8. Understand which session a task belongs to, which defaults apply, and when to reset it.
9. See whether the gateway, remote clients, and paired devices are present, trusted, and healthy.

## 4. Reference Alignment With OpenClaw

This UI should preserve the useful mental model found in the local `openclaw` reference:

- multi-channel assistant controlled through messaging apps
- gateway-centric control surface
- session-centric runtime with explicit session keys, defaults, and session hygiene
- skills as first-class configurable capabilities
- session and agent views for inspecting runtime behavior
- approval and permission concepts for sensitive actions
- presence, typing, pairing, and remote-control concepts as observable system state
- persistent agent context and operational visibility

This product intentionally extends OpenClaw with:

- stronger human-in-the-loop gating for escalation and privileged actions
- clearer agent and sub-agent orchestration visibility
- intention graph exploration
- memory visibility and memory controls
- near one-click onboarding optimized for non-technical users

## 5. Information Architecture

### Global navigation

- Overview
- Tasks
- Sessions
- Agents
- Channels
- Approvals
- Memory
- Skills
- Setup
- Settings

### Cross-cutting persistent UI elements

- top command bar with workspace switcher, global search, connection state, unread approvals
- left navigation rail
- global WebSocket connection indicator
- active task ticker
- emergency pause / stop all button

## 6. Core Screens

### 6.1 Overview

Purpose: a live operational summary.

Key modules:

- system health summary
- active task count
- pending approvals count
- channel health matrix
- recently active agents
- memory write volume
- latest critical events

Primary actions:

- resume setup
- jump to blocked task
- review approval queue
- reconnect channel

### 6.2 Tasks Workspace

Purpose: inspect a user task end-to-end.

Layout:

- task header with title, originating channel, risk level, status, created time
- task timeline with major milestones
- agent tree panel showing parent, agents, sub-agents, and status
- intention graph panel
- action stream panel for logs, tool calls, thoughts, MCP activity
- right-side steering drawer

Task states:

- queued
- running
- waiting_for_approval
- waiting_for_channel
- blocked
- completed
- failed
- cancelled

Task details shown:

- original user request
- current summary from orchestrator
- active channels involved
- memory reads and writes
- tools touched
- approvals requested
- outputs produced

### 6.3 Agent Workspace

Purpose: inspect and steer an individual agent.

Sections:

- agent identity card
- parent/child lineage
- live state and heartbeat
- current intention
- current context window summary
- recent thoughts
- tool and MCP actions
- memory operations
- policy constraints

On click behavior:

- clicking any agent or sub-agent opens a "Change Direction" modal
- the modal contains a text input and optional urgency selector
- submitted text becomes a steer event attached to that agent session
- UI shows whether the steer note was accepted, queued, or ignored

### 6.4 Sessions Workspace

Purpose: make the session model explicit instead of hiding it behind task logs.

Sections:

- session defaults summary
- active and recent session list
- session key breakdown and human-readable labels
- current run state, queue state, and last activity
- per-session overrides such as model, fast mode, verbose level, or routing hints
- session hygiene actions

Required behaviors:

- distinguish main, sub-agent, cron, and channel-derived sessions
- show when a task is reusing an existing session versus starting an isolated run
- support reset/new-session actions with confirmation
- preserve task-to-session and channel-to-session linkage in both list and detail views

### 6.5 Channels Control Center

Purpose: show which channels are active, in use, degraded, or faulty.

Each channel card must show:

- channel name and icon
- configured or not configured
- connected or disconnected
- active traffic or idle
- faulty or healthy
- last inbound and outbound event
- authentication state
- linked agent routes
- quick actions

Required channels for MVP:

- WhatsApp
- Telegram
- Web UI

Extensible model for:

- Slack
- Discord
- Signal
- iMessage
- others from the OpenClaw ecosystem

Channel health states:

- healthy
- active
- idle
- degraded
- reconnecting
- blocked
- faulty
- disabled

Channel views:

- summary grid
- per-channel detail drawer
- event history
- route configuration
- test message flow
- pairing and allowlist status where relevant
- typing and delivery capability indicators

### 6.6 Approvals Inbox

Purpose: a focused queue for human-in-the-loop decisions.

Approval card contents:

- action title in plain English
- agent requesting it
- task it belongs to
- why approval is needed
- exact scope of access being requested
- expected side effects
- expiration timer
- approve, reject, ask agent to revise

Approval categories:

- filesystem escalation
- network access
- channel send
- external account action
- memory mutation with policy implications
- tool install or skill import
- destructive action
- device pairing
- operator scope elevation

Approval detail drawer:

- raw payload
- risk classification
- before and after diff where possible
- sandbox impact
- audit metadata

### 6.7 Memory Console

Purpose: make persisted memory visible and governable.

Sections:

- memory summary
- recent writes
- memory sources
- scoped memories by user, task, agent, and channel
- conflict and stale memory warnings

Actions:

- inspect a memory entry
- pin a memory
- archive a memory
- delete or redact with confirmation
- adjust retention policy

### 6.8 Skills Manager

Purpose: import, inspect, enable, and govern `SKILLS.md` capabilities.

Flows:

- import local `SKILLS.md`
- parse and preview detected skills
- validate metadata and dependencies
- enable globally or per agent
- set approval policy for skill usage
- review skill provenance and version

Each skill card should show:

- name
- source
- summary
- required tools
- risk markers
- status
- compatible agents

### 6.9 Presence And Access

Purpose: show who and what is connected to the gateway, under which trust model, and whether operator control is safe.

Modules:

- gateway connection and auth mode summary
- browser session trust state
- paired device list
- remote access mode such as local, trusted proxy, Tailscale, or password/token auth
- presence table for gateway clients and devices
- recent pairing and auth-related events

Actions:

- inspect requested operator scopes
- approve or revoke pairing
- rotate browser session or gateway token
- open remote-access diagnostics

### 6.10 Setup Wizard

Purpose: support one-click or near one-click onboarding.

Steps:

1. Create workspace
2. Connect primary model/provider
3. Connect WhatsApp
4. Connect optional channels
5. Import skills
6. Set approval defaults
7. Verify memory
8. Finish and launch

Design requirements:

- non-technical copy
- progress persistence
- resumable steps
- inline diagnostics
- no raw config editing unless user opts in
- generated forms should be driven by backend config metadata where possible

## 7. Interaction Model

### Agent tree interaction

- tree nodes show role, status, current intention, and wait state
- selecting a node filters the action stream to that session
- hovering a node highlights sibling and parent relationships
- completed nodes remain visible for audit

### Change direction interaction

- accessible from task workspace and agent workspace
- modal title: "Change Direction"
- body copy explains this sends steering guidance, not a hard reset
- freeform text input
- optional toggles:
  - mark as high priority
  - require acknowledgement
  - apply only to this agent
- submit creates a `steer_agent` event

### Intention graph interaction

Graph model:

- each node represents an intention or sub-intention
- each node contains grouped thoughts, tool calls, MCP calls, and outputs
- edges represent decomposition, dependency, or revision

Node card contents:

- intention title
- owner agent
- status
- counts of grouped actions
- elapsed time
- risk badge if sensitive actions occurred

User actions:

- click node to open grouped action drawer
- filter by agent
- filter by tool type
- toggle between graph and list mode
- compare current intention graph to final task summary

### Realtime behavior

- websocket drives all live surfaces
- optimistic state only for user-issued actions
- stale banners appear on disconnect
- reconnection should preserve task context and scroll position
- presence and typing indicators degrade quietly without blocking primary task inspection
- reconnect flow should replay missed events by cursor where supported

## 8. Functional Requirements

### FR-1 Messaging parity

- The UI must clearly show tasks originating from WhatsApp and other channels.
- The UI must show the latest user-visible message state for each task.
- The UI must support sending task outcomes or approval results back through the originating channel.

### FR-2 Approval gating

- The UI must surface every action requiring escalation before execution.
- The UI must show what access level is being requested and why.
- The UI must let the user approve once, approve for task, or reject where policy allows.

### FR-3 Persistent memory visibility

- The UI must show memory read and write events in context.
- The UI must support scoped filtering by task, channel, user, and agent.
- The UI must make durable memory distinct from temporary context.

### FR-4 Channel observability

- The UI must distinguish active, in-use, idle, degraded, and faulty channels.
- The UI must support per-channel diagnostics and route inspection.
- The UI must expose reconnection and test actions.
- The UI must show pairing posture, allowlist posture, and typing capability for each relevant channel.

### FR-5 Agent hierarchy visibility

- The UI must show all active agents and sub-agents for a task.
- The UI must show spawn relationships and current execution state.
- The UI must support steering any visible agent.

### FR-6 Intention grouping

- The UI must group actions by intention, not just chronologically.
- The grouping model must include thinking, tool calls, MCP calls, and outputs.
- The UI must support graph and list representations of the same grouped data.

### FR-7 Skills import

- The UI must support importing `SKILLS.md`.
- The UI must validate and preview imported skills before enabling them.
- The UI must record skill source and approval requirements.

### FR-8 Session visibility and hygiene

- The UI must expose session defaults, active session keys, and per-session overrides in a user-readable way.
- The UI must distinguish main, isolated, cron, and sub-agent sessions.
- The UI must support safe reset or restart flows without making the user understand raw session key syntax.

### FR-9 Presence, pairing, and operator access

- The UI must surface gateway presence, browser trust state, and paired device state.
- The UI must show when an action requires operator scopes beyond the current browser session.
- The UI must support pairing approval and access revocation with audit history.

### FR-10 Config-driven setup surfaces

- The UI must be able to render setup and settings forms from typed config metadata and UI hints.
- The UI must honor field sensitivity, grouping, ordering, and advanced-field metadata.
- The UI must never reveal secrets in clear text by default, even when the backend exposes editable config.

## 9. Non-Functional Requirements

### Performance

- First meaningful paint under 2.5s on a modern laptop for the overview route
- Task workspace interactive within 1s after route transition
- Live event stream should handle bursty agent activity without locking the UI

### Reliability

- WebSocket reconnect with resumable subscriptions
- event deduplication by event id
- graceful degradation to polling for critical summaries if socket is unavailable

### Accessibility

- WCAG 2.2 AA baseline
- full keyboard access for approvals and agent steering
- graph interactions must have an equivalent list view
- live regions for approval and failure events

### Security

- approval actions require anti-replay protections
- audit history visible but immutable in UI
- privileged scopes always rendered in human-readable form
- channel secrets never rendered in clear text by default
- browser session trust and operator scopes must be visible before privileged actions are offered

## 10. Recommended Frontend Architecture

The frontend should be implemented as a modular monolith with strong domain boundaries.

### Stack

- React + TypeScript
- Vite
- TanStack Router for route boundaries and data preloading
- TanStack Query for server state and cache orchestration
- Zustand for local UI state only
- React Flow for the intention graph and agent topology views
- Tailwind CSS + a small internal design system
- Zod for runtime validation of API and WebSocket payloads
- Vitest + Testing Library for unit and integration tests
- Playwright for critical interaction flows

### Architectural style

Use a feature-sliced architecture with explicit layers:

- `app/` for bootstrap, providers, router, and global wiring
- `pages/` for route-level composition
- `widgets/` for large reusable UI assemblies
- `features/` for user-facing behaviors like approvals, steering, channel diagnostics, session controls, pairing, skill import
- `entities/` for domain models like task, session, agent, channel, memory, skill, approval, presence, operator access
- `shared/` for design system, utilities, event bus, schema helpers, and primitives

### Data boundaries

- REST for initial route hydration and mutations
- WebSocket for live events
- a single typed event translation layer converts raw socket payloads into domain events
- reducers or store adapters fan those events into entity caches
- config forms must adapt backend-provided UI hint metadata into typed frontend field definitions before rendering

### State rules

- server truth belongs in TanStack Query caches
- transient UI state belongs in feature-local Zustand stores or component state
- no direct WebSocket mutation inside presentation components
- all API and socket payloads validated through Zod before use

### Directory shape

```text
src/
  app/
  pages/
  widgets/
  features/
    approvals/
    agent-steering/
    channel-health/
    session-controls/
    pairing-access/
    intention-graph/
    skill-import/
  entities/
    task/
    session/
    agent/
    channel/
    memory/
    approval/
    skill/
    presence/
    operator-access/
  shared/
    api/
    websocket/
    ui/
    lib/
    config/
    schemas/
```

### Component rules

- pages compose widgets and features, but do not contain raw data access logic
- widgets coordinate several features for a screen region
- features own a user interaction from end to end
- entities own domain types, selectors, event mappers, and small reusable domain components
- shared contains no business-specific assumptions

### Realtime rules

- one socket connection per browser session
- subscription manager per task or overview route
- normalized event envelope:
  - `eventId`
  - `eventType`
  - `occurredAt`
  - `taskId`
  - `agentId`
  - `payload`
- event replay support for reconnect or route remount
- route loaders should seed Query caches with both current snapshots and replay cursors for realtime continuity

## 11. Backend Contract Requirements for UI

The frontend expects the backend to provide:

- typed REST resources for tasks, sessions, agents, channels, approvals, memory, skills, setup state, presence, and operator access
- typed WebSocket events for task, session, agent, tool, memory, channel, approval, presence, and pairing lifecycles
- stable ids for task, session, intention node, approval, channel, skill, and presence entries
- intention-grouped activity payloads or enough event metadata for the UI to derive them
- config schemas and UI hints that let the frontend render safe forms without hardcoding every provider and channel option

### Minimum event families

- `task.created`
- `task.updated`
- `task.completed`
- `session.created`
- `session.updated`
- `session.reset`
- `agent.spawned`
- `agent.updated`
- `agent.steer_requested`
- `agent.steer_applied`
- `agent.thought`
- `agent.intention_started`
- `agent.intention_updated`
- `agent.intention_completed`
- `tool.called`
- `tool.completed`
- `mcp.called`
- `mcp.completed`
- `approval.requested`
- `approval.resolved`
- `memory.read`
- `memory.written`
- `channel.updated`
- `channel.health_changed`
- `channel.typing`
- `presence.updated`
- `pairing.requested`
- `pairing.approved`
- `pairing.revoked`
- `operator.access_changed`

## 12. UX Writing Principles

- explain power in plain English
- make risk concrete, not abstract
- use system language consistently:
  - task
  - agent
  - sub-agent
  - channel
  - approval
  - memory
  - skill
  - intention
- never present low-level tool jargon without an adjacent plain-language explanation

## 13. Design Direction

The interface should avoid generic "startup dashboard" styling.

Design guidance:

- editorial, high-contrast typography
- warm neutral base with sharp operational accent colors
- status colors reserved for system meaning
- layered panels with subtle depth
- motion used to communicate live change, not decoration

Suggested visual language:

- graphite, sand, slate, ember, signal green
- monospaced accents for runtime details
- human-readable prose for summaries and approvals

## 14. Delivery Plan

### Phase 1

- overview
- task workspace
- sessions workspace
- approvals inbox
- channels control center
- websocket event backbone

### Phase 2

- memory console
- skills import and management
- setup wizard
- presence and access
- agent steering and acknowledgements

### Phase 3

- intention graph
- advanced channel routing
- multi-workspace support
- replay and audit tools

## 15. Acceptance Criteria

- A user can connect WhatsApp and see task activity in the UI without reading raw logs.
- A user can see all active agents and sub-agents for a task.
- A user can click any agent and submit steering guidance.
- A user can approve or reject escalated actions from the approvals inbox.
- A user can identify which channels are healthy, active, idle, degraded, or faulty.
- A user can inspect memory activity and distinguish temporary context from persistent memory.
- A user can import a `SKILLS.md` file, preview the parsed skills, and enable them safely.
- The UI remains usable during heavy live event traffic and recovers from WebSocket disconnects.

## 16. Guidance for Implementation Agents

- Build for long-term scalability, not a hackathon-only code shape.
- Keep domain logic out of UI components.
- Prefer typed contracts and schema validation over implicit assumptions.
- Implement vertical slices so each feature can ship independently.
- Treat approvals, channel health, memory, task orchestration, sessions, presence, and operator access as first-class domains.
- Optimize for inspectability and testability.
- Design every complex surface with a list fallback before adding a graph or advanced visualization.
- If a task is large, split it into specialist workstreams such as design system, data contracts, realtime state, task workspace, or channel control.
- When the execution environment supports it, actively spawn or delegate to specialist agents for parallelizable work.
- Parent agents should retain orchestration responsibility while delegated agents own isolated subtasks with clear contracts.

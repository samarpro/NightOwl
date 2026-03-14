# NightOwl Session System

This document explains how the session part of NightOwl works — the lifecycle of an agent session, how the spawn-and-wait pattern works, and how completion events flow between parent and child sessions.

## Overview

A **session** is one independent Pydantic AI agent run. When a user sends a message via a channel (e.g. Telegram), the gateway creates a **main** session for that message. The main agent can then spawn **child sessions** that run in parallel on sub-tasks, receive their results asynchronously, and synthesise a final answer.

```
User message
     │
     ▼
SessionManager.create_main_session()
     │
     ▼
run_session()  ──► initial agent.run()
     │                    │
     │            agent calls sessions_spawn()
     │                    │
     │            SessionManager.spawn_child()  ──► child Session (PENDING)
     │
     ▼
session enters WAITING state
     │
     │  (child session runs independently in parallel)
     │
     ▼  child calls manager.complete_session()
SessionManager.deliver_completion_to_parent()
     │
     ▼  message enqueued on parent's asyncio.Queue
run_session() wait loop unblocks
     │
     ▼
agent.run() called again with child completion message + history
     │
     ▼
final answer returned
```

---

## Session Roles

Each session has a role determined by its **depth** in the spawn tree:

| Role | Depth | Can spawn children? |
|------|-------|---------------------|
| `main` | 0 | Yes |
| `orchestrator` | 1 … max-1 | Yes |
| `leaf` | max depth | No |

The default `max_spawn_depth` is 3 (configurable in `config.py`). Role is resolved by `sessions/depth.py`:

```
depth 0               → MAIN
depth 1 … (max-1)     → ORCHESTRATOR
depth ≥ max           → LEAF
```

Leaf agents receive a system prompt instructing them they **cannot spawn** — they must complete their task directly using available tools.

---

## Session Lifecycle

```
PENDING → RUNNING → WAITING → COMPLETED
                           └──────────► FAILED
```

| State | Meaning |
|-------|---------|
| `PENDING` | Session created but agent has not started yet |
| `RUNNING` | Agent is actively running (`agent.run()` in progress) |
| `WAITING` | Agent's first run completed, waiting for child sessions to complete |
| `COMPLETED` | Session finished successfully; `result` is set |
| `FAILED` | Session finished with an error; `result` contains the error message |

---

## How the Spawn-and-Wait Pattern Works

This is the core design — it mirrors OpenClaw's agent swarm model.

### 1. Spawning children

The agent calls the `sessions_spawn` tool with a task description. The tool:

1. Calls `SessionManager.spawn_child()` which creates a new `Session` object (state=`PENDING`)
2. Adds the child's ID to `parent.expected_completions`
3. Returns **immediately** with the child's session ID and a "do NOT poll" instruction

The child session is returned — but note that `run_session()` is **not** called by the spawn tool. It is the caller's responsibility (e.g. the gateway's ingest endpoint) to run child sessions, typically via `asyncio.create_task`.

### 2. Entering the wait loop

After the initial `agent.run()` returns, the runner checks:

```python
if queue and not manager.all_completions_received(session.id):
    session.state = SessionState.WAITING
    while not manager.all_completions_received(session.id):
        message = await asyncio.wait_for(queue.get(), timeout=300)
        result = await agent.run(message, deps=deps, message_history=result.new_messages())
```

- The parent session enters `WAITING` state.
- It blocks on `queue.get()` — an `asyncio.Queue` owned by this session.
- **No polling** — the parent does not call `sessions_list` or sleep. It just waits.

### 3. Child completion events

When a child session finishes, it calls `manager.complete_session(child_id, result)`. This:

1. Sets the child's state to `COMPLETED` or `FAILED`
2. Calls `deliver_completion_to_parent()` which:
   - Removes the child from `parent.expected_completions`
   - Formats a completion message (marked **untrusted** because it came from a child agent)
   - Puts the message on the parent's `asyncio.Queue`

This unblocks the parent's `queue.get()`, and the parent re-runs the agent with the completion message and full message history.

### 4. Synthesising results

The parent agent receives all child completion messages one by one as "user messages" in subsequent `agent.run()` calls. When `all_completions_received()` returns True (i.e. `expected_completions` is empty), the loop exits and the parent's final response is returned.

### Why completions are marked "untrusted"

Child agents can be compromised by prompt injection from external data they process (e.g. a webpage with injected instructions). Marking child output as untrusted reminds the parent agent to validate before acting on it.

---

## Sandbox Inheritance

If a parent session is running in a sandbox (CLI, browser, or computer use), all children it spawns **must also be sandboxed**. This prevents a sandboxed parent from escaping isolation via a non-sandboxed child.

```python
# SessionManager.spawn_child():
if parent.sandbox_mode and parent.sandbox_mode != SandboxMode.NONE:
    if sandbox is None or sandbox == SandboxMode.NONE:
        sandbox = parent.sandbox_mode  # force inherit
```

---

## Spawn Limits

| Limit | Default | Config key |
|-------|---------|------------|
| Max spawn depth | 3 | `max_spawn_depth` |
| Max children per session | 5 | `max_children_per_session` |

Attempts to exceed these limits raise `ValueError` from `SessionManager.spawn_child()`.

---

## Session Tools

All non-leaf agents have access to three session tools:

| Tool | What it does |
|------|-------------|
| `sessions_spawn(task, label?, sandbox?, model?)` | Spawn a child agent session. Returns immediately with child ID. |
| `sessions_list()` | List current children and their status. |
| `sessions_send(session_id, message)` | Send a steering message to a running child. |

The `sessions_spawn` docstring explicitly instructs the agent: **"Wait for the completion event — do NOT poll."**

---

## Broadcast Events

The `SessionManager` emits structured events onto a broadcast `asyncio.Queue` (connected to the WebSocket gateway for the dashboard):

| Event type | When |
|------------|------|
| `session:created` | Main session created |
| `session:spawned` | Child session spawned |
| `session:running` | Session's agent starts executing |
| `session:waiting` | Session entered wait loop |
| `session:completed` | Session completed (success or failure) |

---

## Key Files

| File | Purpose |
|------|---------|
| `sessions/manager.py` | Core orchestrator: session CRUD, spawn, completion delivery, broadcast |
| `sessions/runner.py` | Executes one agent session: initial run + wait loop |
| `sessions/depth.py` | Role resolution from depth (`main`/`orchestrator`/`leaf`) |
| `sessions/prompt_builder.py` | Builds role-scoped system prompts |
| `sessions/tools.py` | `sessions_spawn`, `sessions_list`, `sessions_send` tools |
| `models/session.py` | Data models: `Session`, `SessionRole`, `SessionState`, `SandboxMode`, `SpawnRequest`, `TaskCompletionEvent` |

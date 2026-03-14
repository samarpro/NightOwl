# Sessions

The session system is NightOwl's core engine. It implements OpenClaw's parallel agent swarm model: a main agent spawns independent child sessions that run concurrently, and children push completion events back to the parent when done. The parent never polls.

## Session Lifecycle

```
create_main_session(task)
        │
        ▼
   RUNNING ──spawn_child──► PENDING → RUNNING → COMPLETED
        │                                            │
        │                     completion event ◄─────┘
        │
   WAITING (if children spawned, parent waits for all completions)
        │
   COMPLETED (synthesises child results into final output)
```

Sessions have three roles based on depth:

- **Main** (depth 0) — entry point, can spawn children, orchestrates the full task
- **Orchestrator** (depth 1 to max-1) — child that can itself spawn further children
- **Leaf** (depth = max) — cannot spawn, must complete its task directly

Depth limits and max children per session are enforced by `SessionManager` using values from `config.py`. Sandbox mode is inherited: a sandboxed parent can only spawn sandboxed children.

## Components

### SessionManager (`manager.py`)

Owns all session state and queues. Handles creation, spawning, completion, and event routing. When a child completes, the manager delivers a `TaskCompletionEvent` as a message into the parent's asyncio queue — this is how the parent receives results without polling.

Background child sessions are launched as `asyncio.Task`s via the configurable `_child_runner` callable.

### Runner (`runner.py`)

Executes Pydantic AI agents using `agent.iter()` for streaming node-level visibility. Each node (model request, tool call, end) emits an event via the callback.

Key functions:

- **`process_message`** — the core processing function. Drains pending child completions from the queue first, then feeds the new message through the agent. Used by all entrypoints.
- **`run_child_session`** — entry point for background children. Runs the task, waits for sub-children if any were spawned, then completes.
- **`run_interactive`** — multi-turn REPL loop wrapping `process_message`.

Transient Bedrock errors (429, 5xx) are retried via stamina with exponential backoff.

### Tools (`tools.py`)

Three Pydantic AI tools registered on non-leaf agents:

- **`sessions_spawn`** — spawns a child and returns immediately with its ID
- **`sessions_list`** — lists children and their status
- **`sessions_send`** — sends a steering message to a running child

`AgentState` is the deps dataclass threaded through all tool calls, carrying the session ID, manager reference, and HITL gate.

### Prompt Builder (`prompt_builder.py`)

Generates system prompts scoped to session role. Main agents get the full identity and tool descriptions. Orchestrators get their task context and parent reference. Leaf agents get an explicit "you cannot spawn" instruction.

### Depth Resolution (`depth.py`)

Port of OpenClaw's `resolveSubagentRoleForDepth`. Maps depth integers to session roles and capability flags.

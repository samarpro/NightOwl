# Sessions

The session system is NightOwl's core engine. It implements OpenClaw's parallel agent swarm model: a main agent spawns independent child sessions that run concurrently, and children push completion events back to the parent when done. The parent never polls.

## Session Lifecycle

```
create_main_session(task)
        │
        ▼
   RUNNING ──spawn_child──► PENDING → RUNNING ◄──► WAITING
        │                        │         ▲            │
        │                        │         │    (idle, waiting for messages)
        │                        │         └────────────┘
        │                        │
        │                        └──► COMPLETED (via sessions_complete or idle timeout)
        │                                  │
        │         completion event ◄───────┘
        │         (child slot freed on parent)
        │
   COMPLETED (synthesises child results into final output)
```

Sessions have three roles based on depth:

- **Main** (depth 0) — entry point, can spawn children, orchestrates the full task
- **Orchestrator** (depth 1 to max-1) — child that can itself spawn further children
- **Leaf** (depth = max) — cannot spawn, must complete its task directly

Child sessions are **persistent** — after processing their initial task, they stay alive to handle follow-up messages from the parent and completions from their own children. They exit when the parent calls `sessions_complete`, or after an idle timeout (10 minutes by default). When a child completes, its slot on the parent is freed so new children can be spawned within the limit.

Depth limits and max children per session are enforced by `SessionManager` using values from `config.py`. Sandbox mode is inherited: a sandboxed parent can only spawn sandboxed children.

## Components

### SessionManager (`manager.py`)

Owns all session state and queues. Handles creation, spawning, completion, and event routing. When a child completes, the manager delivers a `TaskCompletionEvent` as a message into the parent's asyncio queue — this is how the parent receives results without polling. Completed children are removed from the parent's children list, freeing the slot for new spawns.

Background child sessions are launched as `asyncio.Task`s via the configurable `_child_runner` callable. The manager also holds references to the `SessionStore` (persistence), `ChannelRegistry`, and `HITLGate`.

On server startup, `load_and_resume()` restores the most recent active main session from the database, including its full message history. Orphaned child sessions (left running from a previous process) are marked as failed.

### Runner (`runner.py`)

Executes Pydantic AI agents using `agent.iter()` for streaming node-level visibility. Each node (model request, tool call, end) emits an event via the callback.

The runner provides two layers of abstraction:

- **`SessionRuntime`** — a stateful wrapper holding an agent, deps, and message history. Created via `create_session_runtime()`. The `IngressService` uses this for long-lived channel sessions.
- **`process_runtime_message`** — runs a single turn through a `SessionRuntime`, updating its history in place.

Lower-level functions:

- **`process_message`** — drains pending child completions from the queue first, then feeds the new message through the agent. Used by the CLI's interactive loop.
- **`run_child_session`** — entry point for background children. Runs the initial task, then enters a persistent wait loop — processing follow-up messages from the parent and sub-child completions. Exits on idle timeout or when the parent calls `sessions_complete`.
- **`run_interactive`** — multi-turn REPL loop wrapping `process_message`.

Transient Bedrock errors (429, 5xx) are retried via stamina with exponential backoff.

### Tools (`tools.py`)

Four Pydantic AI tools for session management (spawn, list, and complete are registered on non-leaf agents; send is available to all):

- **`sessions_spawn`** — spawns a child and returns immediately with its ID
- **`sessions_list`** — lists children and their status
- **`sessions_send`** — bidirectional messaging: send to a child (steering) or to your parent (progress updates, questions). Messages are prefixed with system markers so agents can distinguish parent vs child messages from user messages.
- **`sessions_complete`** — tells a child session to wrap up and exit

`AgentState` is the deps dataclass threaded through all tool calls, carrying the session ID, manager, HITL gate, channel registry, and session store.

### Session Store (`store.py`)

Persistence layer for sessions and chat messages. Writes session state and Pydantic AI `ModelMessage` history to PostgreSQL. On restart, the most recent active main session can be resumed with its full conversation history intact. This gives cross-channel continuity — a user can start a conversation on Telegram and resume after a server restart.

### Prompt Builder (`prompt_builder.py`)

Generates system prompts scoped to session role. Key rules injected into all prompts:

- **Relay rule** — the user cannot see child agent messages; the parent must relay all content verbatim
- **Auth rule** — agents never worry about authentication; the system handles OAuth flows transparently
- **No-poll rule** — parents wait for completion events, never poll

Main agents get the full identity and all tool descriptions. Orchestrators get their task context, parent reference, and can message their parent. Leaf agents get an explicit "you cannot spawn" instruction but can still message their parent.

### Depth Resolution (`depth.py`)

Port of OpenClaw's `resolveSubagentRoleForDepth`. Maps depth integers to session roles and capability flags.

# Models

Pydantic data models shared across the application. Each file maps to a domain.

### `session.py`

Core session types: `Session`, `SessionRole` (main/orchestrator/leaf), `SessionState` (pending/running/waiting/completed/failed), `SandboxMode` (none/cli/browser/computer), `SpawnRequest`, and `TaskCompletionEvent`. These drive the entire session lifecycle in the manager.

### `approval.py`

HITL types: `RiskLevel` (low/medium/high/critical), `ToolCallWithRisk`, `ApprovalRequest`, and `ApprovalResponse`. Used by the classifier, decorator, and gate.

### `message.py`

`Message` for internal session messages (stored in the database) and `ChannelMessage` for normalized inbound messages from channel bridges.

### `observability.py`

Dashboard visualization types: `AgentCard` (session state for the UI), `IntentNode`/`IntentEdge`/`IntentGraph` (directed graph of agent intent for the session tree visualization).

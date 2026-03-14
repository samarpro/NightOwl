# HITL (Human-in-the-Loop)

The HITL system gates high-risk tool calls behind human approval. Before a dangerous action executes, the user must explicitly approve it — either from the web dashboard or inline in their messaging app.

## Risk Classification

Every tool call carries a self-reported risk level from the agent. The system doesn't trust the agent's assessment blindly:

| Risk Level | HITL Required? | Classifier Runs? |
|------------|---------------|-------------------|
| `low` | No (unless classifier escalates) | Yes |
| `medium` | Yes | Yes |
| `high` | Yes | No — already dangerous |
| `critical` | Yes + confirm | No — already dangerous |

For `low` and `medium`, a fast Haiku classifier second-guesses the agent. If Haiku escalates the risk, the action gets gated. For `high` and `critical`, the classifier is skipped — there's no point verifying what's already flagged as dangerous.

## Components

### Decorator (`decorator.py`)

The `@hitl_gated` decorator wraps any Pydantic AI tool function. It intercepts the `risk_level` and `risk_justification` kwargs (provided by the LLM, consumed by the decorator, never passed to the tool), runs the classification logic, and either approves, gates, or denies the call. The tool function itself has zero HITL awareness.

### Classifier (`classifier.py`)

Calls Claude Haiku via Bedrock to verify the agent's self-reported risk. Uses a typed `RiskVerification` Pydantic output model for structured responses. Receives the tool name, args, reported risk, and justification. Returns a verified risk level with reasoning. Falls back to the self-reported risk on any error — the system degrades to trusting the agent rather than blocking all actions.

### Gate (`gate.py`)

`HITLGate` manages the approval lifecycle:

1. Creates a pending approval with a unique ID and expiry timestamp
2. Broadcasts `approval:required` via the event bus (picked up by dashboard WebSocket and CLI)
3. Resolves the session's channel — walks up the parent chain if the approval originates from a child session, so child HITL requests reach the user's messaging app
4. Sends an inline approval request through the appropriate bridge (Telegram inline keyboard, WhatsApp/SMS text prompt)
5. Blocks on an `asyncio.Event` until resolved or timeout
6. First response wins — dashboard, WebSocket, Telegram callback query, and channel all race; whichever responds first takes effect

The gate is shared across all sessions via the `SessionManager` and receives the `ChannelRegistry` at construction time.

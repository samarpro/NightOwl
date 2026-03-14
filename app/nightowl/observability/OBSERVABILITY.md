# Observability

The observability system captures agent activity and classifies it into a live intent graph for the dashboard. This is what makes NightOwl's agent swarm visible — the user can see not just what agents are doing, but *why*.

## Pipeline

```
Agent activity ──► TokenStore (append-only capture)
                        │
                        ▼
                   IntentClassifier (chunk + classify via Haiku)
                        │
                        ▼
                   IntentGraphManager (build graph, broadcast to dashboard)
```

## Components

### Token Store (`token_store.py`)

In-memory append-only store of agent activity per session. Every model request, response, tool call, tool result, spawn, and completion is recorded as a `TokenEntry` with type, content, metadata, and timestamp. The dashboard can query raw tokens via the API for the token viewer.

### Intent Classifier (`intent_classifier.py`)

Chunks the token stream at tool-call boundaries (each chunk = one logical unit of work: thinking → tool_call → tool_result → response). Calls Haiku to classify each chunk into a `ClassifiedIntent`: service, intent, status, and summary. Falls back to deriving intent from tool names if classification fails.

Classified intents are converted to `IntentNode`s (from `models/observability.py`) and linked with sequential `IntentEdge`s.

### Intent Graph Manager (`intent_graph.py`)

`IntentGraphManager` maintains a live `IntentGraph` per session. Processes only new tokens since last classification (incremental). Broadcasts `intent:update` events via the event bus so the dashboard receives graph updates in real-time. Processing is triggered after each agent turn via `schedule_processing()` as a background task.

## API

The observability router (`api/routers/observability.py`) exposes:

- `GET /api/v1/observability/intent-graph/{session_id}` — current intent graph for a session
- `GET /api/v1/observability/intent-graphs` — all session graphs
- `GET /api/v1/observability/tokens/{session_id}?last=N` — recent raw token entries
- `POST /api/v1/observability/intent-graph/{session_id}/process` — manually trigger classification

okay, in the frontend, their is learning.md.
read that file to understand how to connect the backend with the front. 
The feature.
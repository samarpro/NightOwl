# Ingest

The ingress service is the bridge between channel messages and agent sessions. It receives normalized `ChannelMessage`s, resolves them to an existing or new session, and manages a background worker loop per session.

## How It Works

1. A `ChannelMessage` arrives (from a webhook router or the ingest API)
2. `IngressService.ingest()` resolves the message to an existing active session, a DB-resumed session, or creates a new one
3. Maps the session to its originating channel in the `ChannelRegistry` (so replies route back correctly)
4. Persists the channel route to the database for cross-restart continuity
5. Ensures a background worker task is running for that session
6. Pushes the message text into the session's queue

The worker loop drains messages from the queue, runs each through the `SessionRuntime` (agent iteration), emits an `agent:response` event, and sends the reply back through the channel bridge.

## Session Resolution

The service maintains a single main session. On each inbound message:

1. If there's an active in-memory session, reuse it
2. If not, try to resume from the database (first message after a restart)
3. If nothing to resume, create a fresh session

Restored sessions get their full message history passed to the `SessionRuntime`, so the agent picks up where it left off. This gives cross-channel, cross-restart continuity.

# Ingest

The ingress service is the bridge between channel messages and agent sessions. It receives normalized `ChannelMessage`s, resolves them to an existing or new session, and manages a background worker loop per session.

## How It Works

1. A `ChannelMessage` arrives (from a webhook router or the ingest API)
2. `IngressService.ingest()` resolves the message to a session — reuses an active session for the same `channel:sender_id` pair, or creates a new one
3. Maps the session to its originating channel in the `ChannelRegistry` (so replies route back correctly)
4. Ensures a background worker task is running for that session
5. Pushes the message text into the session's queue

The worker loop drains messages from the queue, runs each through the `SessionRuntime` (agent iteration), emits an `agent:response` event, and sends the reply back through the channel bridge.

## Session Reuse

Sessions are keyed by `channel:sender_id`. If a user sends a follow-up message while their session is still active (not completed/failed), the message goes into the existing session — preserving conversation context. Completed sessions are replaced on the next inbound message.

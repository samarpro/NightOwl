# Channels

Channels are the messaging app bridges that connect users to NightOwl. Each channel (Telegram, WhatsApp, SMS) adapts platform-specific webhooks into NightOwl's normalized `ChannelMessage` format and routes outbound agent responses back through the platform's API.

## Status

The channel abstraction is scaffolded but not yet implemented. The `channels/` package currently contains only the `__init__.py`. The `ChannelBridge` ABC and Telegram bridge are tracked in the Channels epic (`Hack48Winners-v9s`).

## Design

Each bridge will be a FastAPI router that:

1. Receives incoming webhooks from the messaging platform
2. Normalizes to `ChannelMessage` (defined in `models/message.py`)
3. Forwards to the session manager for processing
4. Sends outbound agent responses via the platform API

Channel bridges also feed into the HITL gate — when an approval request fires, the gate can send an inline approval prompt back through the user's messaging channel (not just the dashboard).

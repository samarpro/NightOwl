# Composio Tools

Composio's MCP Gateway handles all third-party authentication (OAuth, API keys, token refresh). NightOwl doesn't manage any OAuth flows or token storage directly — Composio does.

## How Agents Use Composio

Agents don't get a static list of MCP tools at startup. Instead, they have two meta-tools:

- **`composio_search_tools`** — discovers available Composio tools by query (e.g., "google calendar", "send email"). Returns tool names, descriptions, and versions.
- **`composio_execute`** — executes a discovered tool by slug with parameters. Wrapped with `@hitl_gated`, so the agent must self-report risk and the HITL system gates dangerous calls.

This search-then-execute pattern means agents dynamically discover capabilities based on what services the user has connected, rather than being preconfigured with a fixed tool set.

## Transparent OAuth

When `composio_execute` fails because the user hasn't connected an account, the system handles it automatically:

1. Initiates an OAuth flow via Composio SDK for the required toolkit
2. Sends the auth link to the user through their messaging channel (or prints it in CLI mode)
3. Waits for Composio to call back to `/api/v1/composio/auth/callback` confirming the connection (webhook mode), or polls the connection status (CLI mode)
4. Retries the original tool call once auth completes

The agent never sees the auth flow — it just gets the tool result after a delay. This is driven by the `_AUTH_RULE` in the system prompt telling agents to never worry about authentication.

## Implementation

`_ComposioClient` is a thin singleton wrapper around the Composio SDK. It caches tool versions to avoid redundant lookups. `AuthWaiter` is a singleton that tracks pending OAuth flows and resolves them when the webhook fires.

Requires `COMPOSIO_API_KEY` and `COMPOSIO_USER_ID` in the environment. `PUBLIC_URL` is needed for webhook-based auth callbacks (e.g., when running behind ngrok).

# Composio Tools

Composio's MCP Gateway handles all third-party authentication (OAuth, API keys, token refresh). NightOwl doesn't manage any OAuth flows or token storage directly — Composio does.

## How Agents Use Composio

Agents don't get a static list of MCP tools at startup. Instead, they have two meta-tools:

- **`composio_search_tools`** — discovers available Composio tools by query (e.g., "google calendar", "send email"). Returns tool names and descriptions so the agent can decide what to use.
- **`composio_execute`** — executes a discovered tool by slug with parameters. Wrapped with `@hitl_gated`, so the agent must self-report risk and the HITL system gates dangerous calls.

This search-then-execute pattern means agents dynamically discover capabilities based on what services the user has connected, rather than being preconfigured with a fixed tool set.

## Implementation

`_ComposioClient` is a thin singleton wrapper around the Composio SDK. It's lazily initialized on first use and requires `COMPOSIO_API_KEY` in the environment.

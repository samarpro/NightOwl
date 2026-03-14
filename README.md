# NightOwl 🦉

NightOwl is [OpenClaw](https://github.com/openclaw/openclaw) made safe, observable, and accessible to non-technical users. It keeps OpenClaw's parallel agent swarm model — where the main agent spawns independent child sessions that run concurrently and push results back — but wraps it in human-in-the-loop approvals, real-time observability, and managed infrastructure.

Users interact through messaging apps (Telegram, WhatsApp, SMS). Agents coordinate via a session manager, execute tools through Composio's MCP gateway, and run sandboxed CLI/browser/computer-use tasks in ephemeral Docker containers. A web dashboard shows the live session tree, agent activity, and pending approval requests.
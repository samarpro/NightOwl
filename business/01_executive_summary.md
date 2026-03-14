# Executive Summary

## One-liner

NightOwl is the control plane for autonomous AI agents — giving teams real-time observability, human-in-the-loop safety, and one-click setup on top of the most powerful open-source agent framework available.

## The Problem

AI agents are the most transformative productivity tool since the internet. But today, using them is a bet: you hand over the keys, walk away, and hope nothing breaks. There's no visibility into what the agent is doing, no way to approve risky actions before they happen, and setup requires deep technical knowledge.

This is especially acute in software engineering. Coding agents can now write, test, and ship code autonomously — but engineering leaders have no way to observe a swarm of agents working across repos, no guardrails when an agent wants to run `rm -rf` or push to main, and no audit trail when something goes wrong.

The result: teams either don't adopt agents (losing competitive advantage) or adopt them recklessly (accepting unquantified risk).

## The Solution

NightOwl wraps OpenClaw — an open-source agent framework with parallel session orchestration, messaging app integration, and CLI/browser/computer use — in a safety and observability layer:

- **Session tree visualisation** — see every agent in the swarm, what it's doing, in real-time
- **Human-in-the-loop approvals** — high-risk actions (push to repo, send a message, run a destructive command) require explicit approval before execution
- **Containerised execution** — agents run in isolated, ephemeral VMs. No access to host systems unless explicitly granted
- **AWS Bedrock Guardrails** — prompt injection, PII, and content moderation handled at the infrastructure layer
- **One-click setup** — no CLI, no config files. Connect your tools via OAuth, point it at your messaging app, go

## Why Now

1. **Agent capability is outpacing trust infrastructure.** Models can now autonomously write and ship code, but the tooling to safely supervise them hasn't kept up.
2. **Enterprise agent adoption is hitting a wall.** Teams want agents but can't justify the risk without observability and approval workflows.
3. **The open-source agent ecosystem is mature enough to build on.** OpenClaw, Pydantic AI, Composio, and Claude's tool-use APIs provide the primitives. The missing piece is the control plane.

## Beachhead: Engineering Teams

While NightOwl is a generalised agent platform, the initial go-to-market focuses on software engineering:

- Coding agents that spin up independent VMs, build features, and QA autonomously
- Real-time observation of what each agent session is doing across your codebase
- Approval gates before agents push code, merge PRs, or modify infrastructure
- Full audit trail for compliance and incident investigation

Engineering teams are the ideal first market because they already understand agents, have the highest pain around unsupervised automation, and will pay for tooling that makes their teams faster without increasing risk.

## Business Model

Freemium SaaS with usage-based scaling:

| Tier | Price | Target |
|------|-------|--------|
| Community | Free | Individual developers, open-source |
| Pro | $29/seat/month | Small teams, startups |
| Team | $79/seat/month | Engineering orgs, advanced controls |
| Enterprise | Custom | SOC2, SSO, on-prem, dedicated support |

Revenue scales with compute (container minutes), agent sessions, and connected integrations.

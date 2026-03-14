# Target Market & Personas

## Beachhead: Engineering Teams Using Coding Agents

### Why engineering first

1. **Highest pain.** Engineers are the earliest adopters of AI agents and are already experiencing the trust gap firsthand. They know what they're missing.
2. **Willingness to pay.** Engineering tooling budgets are substantial. Teams already pay for CI/CD, observability (Datadog, Sentry), and dev environments (Codespaces, Gitpod). Agent observability is a natural extension.
3. **Word-of-mouth distribution.** Engineers talk to engineers. A tool that makes coding agents trustworthy spreads through the same channels as VS Code, Docker, and Cursor.
4. **Clear expansion path.** Once engineering adopts, the same platform extends to ops, support, marketing, and eventually the whole org.

## Primary Personas

### Persona 1: The Engineering Lead — "Alex"

**Role:** Staff Engineer or Engineering Manager at a 20-200 person startup

**Context:** Alex's team has started using coding agents (Claude Code, Copilot Workspace, Devin-likes) but adoption is uneven. Some devs love it, others don't trust it. Alex has no visibility into what agents are doing across the team and can't enforce any safety policies.

**Pain points:**
- Can't see what coding agents are doing across the team
- No way to set guardrails (e.g., "don't push to main without approval")
- Worried about security incidents from unsupervised agent actions
- Wants to increase agent adoption but can't justify the risk to leadership

**What NightOwl gives them:**
- Dashboard showing all agent sessions across the team in real time
- Configurable approval policies by risk level
- Audit trail for compliance and incident review
- Confidence to roll out agents more broadly

**Buying trigger:** A near-miss or incident involving an unsupervised agent, or pressure from leadership to adopt AI while maintaining governance.

---

### Persona 2: The Power User Developer — "Sam"

**Role:** Senior developer who uses agents heavily for personal productivity

**Context:** Sam runs OpenClaw or similar tools daily — spawning agents to research, write code, manage tasks, automate workflows. Sam is productive but flying blind. When an agent swarm is running 5 parallel sessions, Sam has no idea what's happening until it's done.

**Pain points:**
- No visibility into parallel agent sessions
- Has to review large diffs after the fact instead of catching issues in real-time
- Setup for each new tool integration is painful (OAuth, API keys, config)
- Wants computer use and browser automation but worried about giving agents free rein

**What NightOwl gives them:**
- Real-time session tree showing every agent and what it's doing
- HITL approvals for risky actions so Sam can stay in the loop
- One-click Composio integration for connecting tools
- Containerised execution so agents can't break Sam's local environment

**Buying trigger:** Frustration with agent opacity, or a bad experience with an agent running a destructive command.

---

### Persona 3: The Non-Technical Operator — "Jordan"

**Role:** Operations, support, or business role at a tech-forward company

**Context:** Jordan sees the engineering team getting productivity gains from AI agents and wants the same for their workflows — but doesn't have the technical skills to set up CLI tools, manage API keys, or debug agent failures.

**Pain points:**
- Can't use current agent tools (too technical)
- Wants to automate repetitive tasks (email triage, scheduling, data entry)
- Needs to trust that the agent won't send wrong emails or book wrong meetings
- Wants approval workflows before agents take action on their behalf

**What NightOwl gives them:**
- One-click setup with guided OAuth flows
- Messaging app interface (Telegram, WhatsApp) they already know
- Visual dashboard showing what the agent is doing
- Approval prompts for anything consequential

**Buying trigger:** Seeing engineering teammates use agents and wanting the same capability without the technical overhead.

## Market Expansion Path

```
Phase 1 (Now)        Phase 2 (6-12mo)       Phase 3 (12-24mo)
Engineering teams --> Ops & business teams --> Platform play
                                               (any team, any workflow)

Coding agents     --> General automation   --> Industry-specific agents
VM sandboxes      --> Browser automation   --> Full computer use
Individual devs   --> Team deployment      --> Enterprise rollout
```

## Competitive Positioning by Persona

| Persona | Current alternative | Why NightOwl wins |
|---------|-------------------|-------------------|
| Engineering Lead | Manual code review + hope | Real-time observability + approval gates |
| Power User Dev | Raw OpenClaw / Claude Code | Same power, plus visibility and safety |
| Non-Technical | ChatGPT / custom GPTs | Real tool integration, not just chat |

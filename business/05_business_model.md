# Business Model

## Revenue Model: Freemium SaaS + Usage-Based Scaling

NightOwl follows the proven open-core model: the agent runtime and basic dashboard are open-source, the commercial product adds team features, advanced observability, and managed infrastructure.

## Pricing Tiers

### Community (Free)
- Single user
- Local deployment (runs on your machine)
- Basic dashboard (session tree, activity feed)
- HITL approvals
- 3 connected integrations (via Composio)
- Community support

**Purpose:** Adoption. Get individual developers hooked on observability.

---

### Pro ($29/seat/month)
- Everything in Community
- Unlimited integrations
- Session history and search (30 days)
- Configurable risk policies
- Priority container scheduling
- Email support

**Purpose:** Convert power users who want persistence and more integrations.

---

### Team ($79/seat/month)
- Everything in Pro
- Team dashboard (see all members' agent sessions)
- Shared approval policies and templates
- Audit trail and compliance exports
- Role-based access control
- SSO (Google, GitHub, Okta)
- 90-day session history
- Slack/Teams integration for approval notifications
- Priority support

**Purpose:** Engineering teams who need shared observability and governance.

---

### Enterprise (Custom pricing)
- Everything in Team
- On-premise / VPC deployment
- SOC2 Type II compliance
- Custom guardrail configuration
- Unlimited session history
- Dedicated support and onboarding
- SLA guarantees
- Custom integrations

**Purpose:** Large organisations with compliance requirements.

## Usage-Based Revenue Components

On top of seat pricing, usage-based charges scale with actual consumption:

| Component | Pricing Model | Notes |
|-----------|--------------|-------|
| Container minutes | Per-minute billing | Sandboxed execution time for CLI/browser/computer use |
| Agent sessions | Included up to tier limit, then per-session | Encourages adoption, monetises heavy usage |
| LLM inference | Pass-through + margin | Bedrock costs passed through with ~20% margin on managed deployment |
| Storage | Per-GB for session history | Audit trails and replay data |

## Unit Economics (Indicative)

### Cost per active user per month (estimated)

| Cost component | Estimate |
|----------------|----------|
| LLM inference (Bedrock) | $5-15 (varies with usage) |
| Container compute | $2-8 |
| Composio MCP Gateway | $1-3 |
| Infrastructure (hosting, DB, WebSocket) | $1-2 |
| **Total COGS per user** | **$9-28** |

### Margin by tier

| Tier | Revenue/user | Est. COGS | Gross margin |
|------|-------------|-----------|-------------|
| Pro ($29) | $29 | ~$15 | ~48% |
| Team ($79) | $79 | ~$22 | ~72% |
| Enterprise | $150+ | ~$30 | ~80% |

Margins improve with scale (infrastructure amortisation) and shift toward enterprise.

## Revenue Projections (Illustrative)

### Year 1 — Establish community and early revenue
- 2,000 Community users
- 200 Pro conversions (10% conversion)
- 30 Team seats (3 small teams)
- **ARR: ~$100K**

### Year 2 — Team adoption accelerates
- 15,000 Community users
- 1,500 Pro users
- 500 Team seats
- 5 Enterprise contracts
- **ARR: ~$1.2M**

### Year 3 — Platform expansion
- 50,000+ Community users
- 5,000 Pro users
- 3,000 Team seats
- 25 Enterprise contracts
- **ARR: ~$6-8M**

## Why This Model Works

1. **Free tier drives adoption.** Engineers try NightOwl individually, get hooked on observability, and pull it into their team.
2. **Team features drive upgrades.** Shared visibility and approval policies are only valuable with multiple people — natural upsell trigger.
3. **Usage-based aligns with value.** Teams that get more value (more agent sessions, more compute) pay more. No shelfware.
4. **Enterprise is the long game.** Compliance, SSO, and on-prem unlock large contracts with high margins.

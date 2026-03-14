---
name: deep-research
description: "Deep research on any topic: spawns parallel child agents to investigate multiple angles, then synthesizes findings into a comprehensive briefing."
metadata:
  { "nightowl": { "emoji": "🔬", "category": "research" } }
---

# Deep Research

Conduct thorough, multi-angle research on a topic by spawning parallel investigator children.

## When to Use

Use this skill whenever:
- The user asks you to research, investigate, or learn about something
- You need to understand a topic before acting on it
- A question requires cross-referencing multiple sources
- The user asks "what are my options", "how does X work", "what's the best way to..."
- You're uncertain about a domain and need to build understanding before proceeding

## Strategy

### 1. Decompose the question into 2-5 independent research angles

Before spawning, think about what distinct lines of inquiry would fully cover the topic. Good decompositions are **orthogonal** — each child investigates something different.

Examples:
- "Best database for real-time analytics" → child-1: compare columnar DBs (ClickHouse, DuckDB, Druid), child-2: compare time-series DBs (TimescaleDB, InfluxDB), child-3: check cloud-managed options and pricing
- "How does NextAuth work?" → child-1: read NextAuth docs + architecture, child-2: find real-world usage patterns in open-source repos, child-3: check known issues and gotchas
- "Should we migrate from REST to GraphQL?" → child-1: research GraphQL trade-offs, child-2: audit our current REST API surface, child-3: find migration case studies

### 2. Spawn children with focused task descriptions

Each child gets a clear, self-contained task. Include:
- **What** to research
- **Where** to look (web search, GitHub, specific docs, specific repos)
- **What to return** — the format you expect (bullet points, comparison table, pros/cons)

Use descriptive labels: `research-columnar-dbs`, `audit-rest-endpoints`, `read-nextauth-docs`.

### 3. Wait for all completions

Do NOT poll. Track expected child IDs and wait for all `TaskCompletionEvent` messages.

### 4. Synthesize

Once all children report back:
- **Cross-reference** findings — look for agreement and contradiction between children
- **Identify gaps** — if an angle was missed or a child came back thin, spawn a follow-up child
- **Rank and recommend** — don't just dump information; give the user your assessment
- **Cite sources** — attribute findings to specific children or sources so the user can dig deeper

### 5. Present as a structured briefing

Format:
```
## Research: {topic}

### Key Findings
- ...

### Comparison (if applicable)
| Option | Pros | Cons | Verdict |

### Recommendation
...

### Open Questions
- Things that need further investigation or user input
```

## Important Rules

- **Always spawn at least 2 children** — single-threaded research defeats the purpose
- **Never present raw child output** — always synthesize and add your own analysis
- **Spawn follow-up children** if initial results are incomplete or contradictory
- **Be honest about confidence** — flag when findings are thin or sources disagree
- **Prefer primary sources** (official docs, source code, APIs) over blog posts and opinions
- Children should use `bash_exec` for web searches, reading repos, and fetching docs

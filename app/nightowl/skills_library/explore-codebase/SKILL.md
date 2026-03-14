---
name: explore-codebase
description: "Explore and understand a codebase: spawns parallel children to scan structure, trace data flows, read key files, and map architecture."
metadata:
  { "nightowl": { "emoji": "🗺️", "category": "development" } }
---

# Explore Codebase

Rapidly build a mental model of a codebase by spawning parallel children to investigate different aspects concurrently.

## When to Use

Use this skill whenever:
- Working with an unfamiliar repo for the first time
- The user asks "how does this project work", "where is X defined", "what's the architecture"
- You need to understand a codebase before making changes
- Tracing how a feature works end-to-end across multiple files
- Investigating a bug that could live in multiple layers

## Strategy

### 1. Start with a structural scan

Spawn a child to map the high-level structure:
- Task: "List the top-level directory structure, read the README, check for config files (package.json, pyproject.toml, Cargo.toml, Makefile, docker-compose), and report: language/framework, build system, entry points, directory layout."
- Label: `scan-repo-structure`

### 2. Spawn targeted investigation children in parallel

Based on what you need to understand, spawn 2-4 children for specific angles:

**Architecture mapping:**
- `trace-entry-points` — Find main entry points (main.py, index.ts, cmd/), trace the startup flow, identify the core abstractions
- `map-data-models` — Find model/schema/type definitions, understand the domain objects and their relationships
- `scan-api-surface` — Find route definitions, API handlers, RPC services; map the public interface

**Feature tracing:**
- `trace-feature-{name}` — Follow a specific feature from UI → API → business logic → data layer
- `find-{pattern}` — Search for specific patterns, function names, or conventions across the codebase

**Dependency analysis:**
- `audit-dependencies` — Read lock files, check for key libraries, understand the tech stack
- `check-test-coverage` — Find test directories, understand testing patterns, check what's covered

### 3. Synthesize into an architecture briefing

Once children report back, synthesize into a clear map:

```
## Codebase: {repo name}

### Tech Stack
- Language, framework, key libraries

### Architecture
- High-level diagram (text-based)
- Key abstractions and how they connect

### Directory Map
- What lives where, organized by concern

### Entry Points
- How the app starts, key files to read first

### Data Flow
- How a request/event flows through the system

### Notable Patterns
- Conventions, idioms, or architectural decisions worth knowing
```

### 4. Spawn follow-up children for deeper dives

If the user asks about a specific area, spawn a focused child to go deeper. Don't re-explore the whole codebase — build on what you already know.

## Important Rules

- **Use file-reading tools, not guessing** — children should actually read files, not infer from names
- **Spawn by concern, not by directory** — "trace the auth flow" is better than "read the auth/ directory"
- **Report file paths** — always include exact paths so the user can navigate directly
- **Note surprises** — flag anything unusual: dead code, circular dependencies, missing tests, inconsistent patterns
- **Respect .gitignore** — don't waste time on node_modules, build artifacts, or vendor directories
- Children should use `bash_exec` with `find`, `grep`, `cat`, `tree` for fast codebase navigation

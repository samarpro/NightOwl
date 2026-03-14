# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Feature Reference

Before implementing, changing, or reviewing any feature work in this repository, agents MUST consult the local `openclaw` repository in `/Users/samkanu/Projects/Hack48Winners/openclaw` for relevant feature behavior, flows, and reference details.

## Frontend Architecture Mandate

For frontend and UI work, agents MUST follow the project architecture defined in [docs/FRONTEND_SPEC.md](/Users/samkanu/Projects/Hack48Winners/docs/FRONTEND_SPEC.md).

Required architecture:

- React + TypeScript frontend
- modular monolith with feature-sliced structure
- route composition in `pages/`
- reusable screen assemblies in `widgets/`
- user-facing behaviors in `features/`
- domain models and typed adapters in `entities/`
- primitives, schemas, shared UI, and infrastructure in `shared/`
- TanStack Query for server state
- WebSocket event translation layer for realtime updates
- Zod validation for REST and WebSocket payloads

Implementation rules:

- Keep business logic out of render components.
- Do not let raw WebSocket payloads flow directly into UI components.
- Model tasks, agents, approvals, channels, memory, and skills as separate domains.
- Prefer small, testable modules over large route files.
- Add or update tests for domain logic, reducers, and critical interactions.
- Preserve accessibility and provide list-based fallbacks for graph-heavy interfaces.

## Delegation Guidance

Agents are explicitly allowed and encouraged to decompose large work into parallel subtasks.

Delegation rules:

- Split large features into clear vertical slices with well-defined contracts.
- Use specialist agents or equivalent delegated workstreams when the environment supports it.
- Keep one orchestrating agent responsible for integration decisions and final verification.
- Delegate independent areas such as design system, realtime state, approvals, channels, memory, or skills import when possible.
- Document assumptions and integration boundaries before parallel work begins.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

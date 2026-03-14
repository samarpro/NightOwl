# Skills

Skills are user-importable instruction sets that teach agents how to perform specific tasks. They follow the OpenClaw SKILL.md convention: YAML frontmatter (name, description, metadata) plus a markdown body with detailed instructions.

## Two-Tier Access

Skills are loaded into agent context in two tiers to manage token budget:

1. **Tier 1 (system prompt)** — skill names and descriptions are injected into the system prompt on every turn. The agent knows what skills exist but doesn't get the full body.
2. **Tier 2 (on-demand)** — the agent calls `load_skill` to fetch the full instructions for a specific skill when it decides to use one. `read_skill_resource` loads bundled assets (scripts, references).

## Components

### Parser (`parser.py`)

Extracts YAML frontmatter and markdown body from SKILL.md files. Validates the name format (lowercase alphanumeric with hyphens), parses metadata, and returns a `ParsedSkill` dataclass.

### Store (`store.py`)

`SkillStore` provides async CRUD for skills and skill resources in PostgreSQL. Skills are upserted by name. Supports enable/disable toggling, resource attachment, and deletion with cascade.

### Loader (`loader.py`)

Scans `skills_library/` on startup for built-in SKILL.md files and upserts them into the database. Custom skills uploaded via the API coexist alongside built-ins.

### Tools (`tools.py`)

Two Pydantic AI tools registered on all agents:

- **`load_skill`** — fetches the full skill body by name
- **`read_skill_resource`** — loads a bundled resource from a skill

`format_skills_for_prompt()` generates the tier 1 prompt section from skill metadata.

## API

The skills API (`api/routers/skills.py`) provides a CRUD interface for the dashboard:

- `GET /api/v1/skills/` — list all skills
- `GET /api/v1/skills/{name}` — get full skill details
- `POST /api/v1/skills/upload` — upload a SKILL.md file
- `POST /api/v1/skills/` — create from raw content
- `DELETE /api/v1/skills/{name}` — delete a skill
- `PATCH /api/v1/skills/{name}/toggle` — enable/disable

## Built-in Skills

Built-in skills live in `skills_library/<name>/SKILL.md` and are loaded on startup. The `night-out` demo skill is included.

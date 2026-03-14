# Documentation Standards

> Rules for writing NightOwl technical documentation. Claude must follow these when producing any `.md` doc in this repo.

## Core Principle

Documentation exists to transfer understanding, not to prove thoroughness. Every sentence must earn its place. If a reader's eyes glaze over, the doc has failed.

## Rules

### 1. Lead with intent, not implementation

Open every section by explaining *what the thing does and why it exists*. Implementation details follow only if they aren't obvious from reading the code. The code is the source of truth for *how* — docs cover *what* and *why*.

### 2. No example code dumps

Do not paste blocks of code into documentation. If a reader needs to see the code, point them to the file and let them read it. A doc that's 40% code blocks is a codebase tour, not documentation.

### 3. One level of abstraction per section

Each section should operate at a single level of abstraction. Don't jump from architecture overview to function signatures in the same paragraph. If you need to go deeper, make it a subsection — and question whether it's needed at all.

### 4. Underwrite, don't overwrite

Say it once, say it clearly, move on. No restating in different words. No "in other words" or "to put it another way". No introductory filler ("In this section we will discuss..."). No concluding summaries of what was just said.

### 5. Respect the reader

Assume the reader is a competent engineer who can follow code. Don't explain what a function does line-by-line. Don't define terms they already know. Don't add warnings about things that are obvious from context.

### 6. Structure carries meaning

Use headings, short paragraphs, and whitespace to make docs scannable — but scannable because they're well-structured, not because they need to be skimmed. A doc that must be skimmed is a doc that's too long.

### 7. Diagrams over prose for architecture

When describing how components connect, use ASCII diagrams or Mermaid. Three sentences describing data flow is worse than one diagram showing it.

### 8. Keep docs next to what they document

Architecture docs live in `docs/`. Component-level docs (if ever needed) live in the component's directory. Don't create a documentation graveyard in a separate tree.

### 9. No staleness traps

Don't document things that change faster than docs get updated — config values, API response shapes, CLI flag lists. Instead, point to where the authoritative version lives (the code, the OpenAPI spec, `--help` output).

### 10. One doc, one purpose

Each document answers one question. `SPEC.md` answers "what are we building and why". An architecture doc answers "how do the pieces fit together". Don't create omnibus docs that try to be everything.

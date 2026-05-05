---
name: agents
description: Always-loaded project anchor. Read this first. Contains project identity, non-negotiables, commands, and pointer to ROUTER.md for full context.
last_updated: 2026-05-05
---

# Metagit CLI

## What This Is
Metagit CLI manages and validates repository/workspace metadata (`.metagit.yml`) and exposes that context to humans and agents, including via MCP runtime tooling.

## Non-Negotiables
- Never commit secrets, tokens, or credential material into repo-tracked files.
- Keep `.metagit.yml` / config model compatibility intact; do not bypass validation paths.
- Keep mutating repo operations explicitly guarded (especially MCP sync modes).
- Put business logic in `src/metagit/core/*`; keep CLI command handlers thin.
- Run lint + relevant tests before claiming a change is complete.
- Default commit messages to patch semantics (`fix:`). Use `feat:` only for additive backward-compatible changes, and use major/breaking prefixes only when schema/config compatibility is intentionally broken.

## Commands
- Setup: `./configure.sh && task install`
- Lint: `task lint`
- Format: `task format`
- Tests: `task test`
- Build: `task build`
- MCP runtime: `uv run metagit mcp serve --status-once`

## Scaffold Growth
After every task: if no pattern exists for the task type you just completed, create one. If a pattern or context file is now out of date, update it. The scaffold grows from real work, not just setup. See the GROW step in `ROUTER.md` for details.

## Navigation
At the start of every session, read `ROUTER.md` before doing anything else.
For full project context, patterns, and task guidance — everything is there.

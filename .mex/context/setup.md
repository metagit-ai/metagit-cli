---
name: setup
description: Dev environment setup and commands. Load when setting up the project for the first time or when environment issues arise.
triggers:
  - "setup"
  - "install"
  - "environment"
  - "getting started"
  - "how do I run"
  - "local development"
edges:
  - target: context/stack.md
    condition: when specific technology versions or library details are needed
  - target: context/architecture.md
    condition: when understanding how components connect during setup
  - target: context/conventions.md
    condition: when setup issues are caused by project-specific command/style rules
last_updated: 2026-05-05
---

# Setup

## Prerequisites
- Python 3.12+ (project requires `>=3.12`).
- `uv` package/environment manager (used for install/run/test/lint commands).
- `task` CLI (Taskfile runner used for standard project workflows).
- Git (required for repository features and many metagit operations).

## First-time Setup
1. `./configure.sh`
2. `task install`
3. `uv pip install -e ".[test]"`
4. `task lint`
5. `task test`

## Environment Variables
- `GITHUB_PERSONAL_ACCESS_TOKEN` (conditionally required) — used by `task start:mcp` for GitHub MCP server container.
- `LEGACY_YAML_LOADER` (optional) — toggles legacy duplicate-key behavior in custom YAML loader.
- `.env` / `.SECRETS.env` (optional/conditional) — loaded by Taskfile; values depend on enabled workflows/providers.

## Common Commands
- `task lint` — runs `ruff check` and `ruff format --check`.
- `task format` — formats code with `ruff format`.
- `task test` — installs test extras and runs pytest suite.
- `uv run metagit --help` — verifies CLI entrypoint and available commands.
- `uv run pytest tests/core/mcp -v` — focused MCP runtime/service regression suite.
- `task docs` — builds docs with mkdocs after schema generation.

## Common Issues
**`task lint` fails after runtime edits:** run `uv run ruff format src/metagit/core/mcp/runtime.py` then rerun `task lint`.  
**MCP command blocks in tests/manual checks:** use `metagit mcp serve --status-once` for non-blocking state diagnostics.  
**Config validation failures during workspace/MCP flows:** validate and inspect `.metagit.yml` shape via `uv run metagit config validate` and model-driven fixes.  
**Tooling mismatch after dependency changes:** run `uv sync` then rerun `task install` to restore expected environment.

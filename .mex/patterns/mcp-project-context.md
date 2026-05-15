---
name: mcp-project-context
description: Add or operate MCP project context switch, session store, and workspace snapshot tools.
triggers:
  - "project context switch"
  - "workspace snapshot"
  - "metagit_project_context_switch"
edges:
  - target: context/mcp-runtime.md
    condition: when changing runtime schemas, dispatch, or services
  - target: patterns/add-mcp-tool.md
    condition: when adding another MCP tool in the same area
last_updated: 2026-05-15
---

# MCP Project Context

## Context
Load `context/mcp-runtime.md`. Core code lives in `session_store.py`, `project_context.py`, `workspace_snapshot.py`, and `context_models.py`.

## Steps
1. Extend Pydantic models in `context_models.py` for any new persisted fields.
2. Update `SessionStore` paths under `.metagit/sessions/` — never store secret values.
3. Implement behavior in `ProjectContextService` / `WorkspaceSnapshotService`; keep git restore out of scope (metadata only).
4. Register tool schema + dispatch in `runtime.py` and `tool_registry.py`.
5. Add unit tests under `tests/core/mcp/services/` and runtime tests in `test_runtime.py`.

## Gotchas
- `metagit_workspace_state_restore` does not checkout branches or reset dirty repos.
- `project_name` session filenames must match `^[\w.-]+$`.
- Env exports skip sensitive variable refs and session overrides are validated.

## Verify
- [ ] `uv run pytest tests/core/mcp/services/test_project_context.py tests/core/mcp/services/test_workspace_snapshot.py tests/core/mcp/test_runtime.py -q`
- [ ] Skills and `docs/cli_reference.md` mention new tools when behavior is user-visible.

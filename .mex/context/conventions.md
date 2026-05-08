---
name: conventions
description: How code is written in this project — naming, structure, patterns, and style. Load when writing new code or reviewing existing code.
triggers:
  - "convention"
  - "pattern"
  - "naming"
  - "style"
  - "how should I"
  - "what's the right way"
edges:
  - target: context/architecture.md
    condition: when a convention depends on understanding the system structure
  - target: context/stack.md
    condition: when selecting libraries/tools for a change
  - target: patterns/INDEX.md
    condition: when implementing task-specific workflows and verify/debug sequences
last_updated: 2026-05-05
---

# Conventions

## Naming
- Python files/modules/functions/variables use **snake_case**; classes use **PascalCase**.
- CLI subcommand modules are one file per command under `src/metagit/cli/commands/` (e.g., `project.py`, `mcp.py`).
- Private class members and internals are prefixed with `_` (consistent with core services/runtime patterns).
- Config file names are explicit (`.metagit.yml`, `metagit.config.yaml`, schema files under `schemas/`).

## Structure
- CLI entrypoint stays in `src/metagit/cli/main.py`; reusable logic belongs in `src/metagit/core/*`, not command functions.
- Each core concern is grouped by component directory (`config`, `detect`, `record`, `mcp`, `utils`, etc.) with focused manager/service classes.
- Tests live in centralized `tests/` and mirror module responsibility by filename (`test_*`), not colocated beside source files.
- MCP runtime flow is split into thin runtime dispatch + dedicated service classes (`workspace_index`, `workspace_search`, `upstream_hints`, `repo_ops`).

## Patterns
Prefer explicit exception-return handling in manager/service methods (consistent with existing union return style):
```python
result = manager.load_config()
if isinstance(result, Exception):
    return result
return result
```

Use state-based gating before exposing tool actions in MCP/runtime logic:
```python
allowed = set(registry.list_tools(status=status))
if tool_name not in allowed:
    raise InvalidToolArgumentsError(...)
```

Use bounded operations for search/sync style tasks:
```python
hits = search_service.search(query=query, repo_paths=paths, max_results=25)
if mode in {"pull", "clone"} and not allow_mutation:
    return {"ok": False, "error": "..."}
```

## Verify Checklist
Before presenting any code:
- [ ] New/changed CLI behavior is covered by command-level tests under `tests/cli` or integration tests when flow crosses modules.
- [ ] Core logic changes are covered by targeted unit tests under `tests/` for the touched service/manager/runtime area.
- [ ] `.metagit.yml`/config model interactions still pass validation paths (no silent schema drift).
- [ ] Lint/format checks pass via project commands (`task lint`, and format if needed).
- [ ] Mutating operations remain explicitly guarded (especially MCP sync/tool paths).
- [ ] Run `task qa:prepush` for session closeout before push/hand-off.

## Commit Semantics
- Default to `fix:` commit prefixes (patch intent) for normal maintenance and safe behavior updates.
- Use `feat:` only for additive backward-compatible capabilities.
- Use `type(scope)!:` or `BREAKING CHANGE:` only when changes intentionally break schema/config compatibility.

---
name: component-resolution
description: Longest-match path→component resolve and identity lookup (RFC-0027 ComponentResolver).
triggers:
  - "component resolve"
  - "ComponentResolver"
  - "RFC-0027"
  - "longest-match"
edges:
  - target: "component-model.md"
    condition: when catalog, identity, or path normalize behavior is involved
  - target: "add-cli-command.md"
    condition: when adding metagit component list|show|resolve CLI
  - target: "add-mcp-tool.md"
    condition: when adding metagit_component_list|show|resolve
  - target: "../context/conventions.md"
    condition: when writing or reviewing resolver code
last_updated: 2026-09-06
---

# Component resolution (RFC-0027)

## Context

Design: `docs/superpowers/specs/2026-09-06-rfc-0027-component-resolution-design.md`.
Plan: `docs/superpowers/plans/2026-09-06-rfc-0027-component-resolution.md`.
Depends on RFC-0026 catalog (`ComponentCatalog`, `ResolvedComponent`), `parse_component_id`, `normalize_repo_relative_path`.

Service: `src/metagit/core/component/resolve.py`. Tests: `tests/core/component/test_resolve.py`.
CLI: `src/metagit/cli/commands/component.py` (`list|show|resolve`). Tests: `tests/cli/commands/test_component_cli.py` (subprocess, not CliRunner).
MCP: ACTIVE `metagit_component_list|show|resolve` in `tool_registry.py` + `runtime.py`. Tests: `tests/core/mcp/test_component_tools.py` (`MetagitMcpRuntime`, `tools/list`, `tools/call`).
Web: GET `/v3/ops/components` and GET `/v3/ops/components/resolve` in `OpsWebHandler` (`src/metagit/core/web/ops_handler.py`). Tests: `tests/core/web/test_ops_components.py` (`_start_server` + urllib). Register `/resolve` before the list route.

## Steps

1. Put matching logic only in `ComponentResolver`. CLI/MCP/web stay thin adapters.
2. `list` filters catalog rows by optional project/repo (unknown filters → empty list).
3. `get` accepts `project/repo/component`. A bare name (no `/`) is unique-name lookup, not a parse error.
4. `resolve` longest-matches normalized POSIX paths. Optional `definition_root` maps an existing filesystem path onto a repo checkout first.
5. No match → `None`. Invalid/escaping paths and ambiguous names/paths → `ValueError`.
6. CLI adapters import resolver from `metagit.core.component.resolve` (not the package `__init__`). Put `--config-path/-c` on **each** `list|show|resolve` subcommand so `component list -c FILE` works; group-level `-c` is optional extra. Load via `MetagitConfigManager` + `resolve_definition_root`; JSON via `emit_json`.
7. MCP adapters import the same symbols, require ACTIVE workspace/config, and pass `status.root_path` as `definition_root`. Schemas use `additionalProperties: false`.
8. Web adapters call the same resolver from `OpsWebHandler`. Missing `path` and `ValueError` are HTTP 400; unmatched resolve is 200 with `matched: false`.

## Gotchas

- Do not import `catalog` or `resolve` from `metagit.core.component.__init__` (circular: `config.models` → `ProjectPath` → package `__init__` → catalog → `MetagitConfig`).
- Store `(_path_rank(normalized), row)` while iterating; do not re-normalize in `max`.
- Whole-repo `.` matches everything in that repo but loses to a longer prefix.
- Fully scoped only when both `project` and `repo` are set (or filesystem mapping returns both **and** agrees with any caller filters). A lone `--project` or `--repo` stays ambiguous: 0 winners → `None`, 1 → that row, 2+ → `ValueError`.
- Filesystem mapping must not overwrite caller `project`/`repo`. Disagreement → no match (`None`). Do not probe process cwd when `definition_root` is set (MCP/web cwd is not a user input).
- Application `paths[]` adapter identity is `{config.name}/{config.name}/{entry.name}`.
- Repos with no `components` never match; list is empty.
- CLI tests must use subprocess + `sys.executable -m metagit.cli.main` (UnifiedLogger enqueue can race under CliRunner).
- Click treats `-c` after the subcommand as a **subcommand** option; group-only `-c` yields `No such option: -c` for `component list -c FILE`.
- Resolve match JSON must put query `path` **after** the payload spread: `{"matched": True, **resolved_component_payload(row), "path": query}` so the component root stays on `spec.path`.
- MCP `matched: false` is a normal `tools/call` result. Show-not-found and `ValueError` are `InvalidToolArgumentsError` (`-32602`).

## Verify

- [ ] `uv run pytest tests/core/component/test_resolve.py tests/core/component/test_catalog.py tests/cli/commands/test_component_cli.py tests/core/mcp/test_component_tools.py tests/core/web/test_ops_components.py -v`
- [ ] `task qa:prepush` (or `zsh ./scripts/prepush-gate.zsh` if `task` mise shims fail)

## Debug

- ImportError on `metagit.core.component.resolve` usually means the module is missing or imported via package `__init__` (do not add that import).
- Ambiguous `get("web")` means two catalog rows share the name; use the full id or project/repo filters.
- CLI `No such command 'component'`: register `component_group` in `src/metagit/cli/main.py`.

## Update Scaffold

- [ ] `.mex/ROUTER.md` project state
- [ ] `docs/concepts/components.md` when operator-facing CLI exists
- [ ] modality `component_resolve` (shipped with CLI/MCP/web)

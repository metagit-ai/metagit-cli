# Context Packs and Repo Cards — Design Spec

**Date:** 2026-05-21  
**Status:** Approved for implementation  
**Scope:** Phase 1 — T0 workspace map + T1 repo cards (CLI + MCP)

## Problem

Agents working across metagit-managed workspaces often receive either too little context (manifest-only) or too much (repomix/`llm.txt` dumps). Humans and agents need a shared, token-budgeted view of the project landscape that is deterministic, structured, and cheap to consume at session start.

## Goals

1. **T0 workspace map** — compact JSON (~100–400 tokens) listing workspace name, projects, repos, roles/tags, clone status.
2. **T1 repo cards** — per-repo structured summaries (~200–600 tokens each) with stack hints, git state, commands, agent instruction excerpt, health flags.
3. **Unified `context pack` API** — CLI and MCP surfaces with `--tier 0|1`, optional `--project`, `--repo`, `--json`.
4. **Strict reuse** — compose existing services; no new heavy detection in v1.

## Non-goals (Phase 1)

- T2 task-scoped slices (changed files, upstream deps) — future phase
- T3 deep retrieval (GitNexus query, repomix profiles) — future phase
- Objectives / approval queue — future phase
- Web UI panels — future phase (API shape should be Web-ready)

## Architecture

```
CLI (context pack) ──┐
MCP (metagit_context_pack) ──┼──► ContextPackService
MCP (metagit_repo_card) ─────┘         │
                                       ├── tier 0: WorkspaceMapService
                                       └── tier 1: RepoCardService
                                                │
                    WorkspaceCatalogService ◄──┤
                    WorkspaceIndexService ◄────┤
                    inspect_repo_state ◄───────┤
                    MetagitConfig (manifest) ◄─┘
```

### Component placement

| Component | Path |
|-----------|------|
| Models | `src/metagit/core/context/models.py` |
| Repo card builder | `src/metagit/core/context/repo_card_service.py` |
| Workspace map builder | `src/metagit/core/context/workspace_map_service.py` |
| Pack orchestrator | `src/metagit/core/context/context_pack_service.py` |
| CLI | `src/metagit/cli/commands/context.py` |
| MCP dispatch | `src/metagit/core/mcp/runtime.py` |

## Data models

### `WorkspaceMapEntry` (repo row in T0)

- `project_name`, `repo_name`, `repo_path`, `status`, `exists`, `tags` (optional list)

### `WorkspaceMapResult` (T0)

- `tier: 0`, `workspace_name`, `workspace_root`, `config_path`
- `project_count`, `repo_count`
- `projects`: list of `{name, repo_count, description?}`
- `repos`: list of `WorkspaceMapEntry`
- `active_project` (from session meta, optional)

### `RepoCardResult` (T1)

- `tier: 1`, `project_name`, `repo_name`, `repo_path`
- `status`, `exists`, `is_git_repo`
- `branch`, `dirty`, `ahead`, `behind`, `head_commit_age_days`
- `tags`, `url`, `description` (from manifest when present)
- `agent_instructions_excerpt` (first 500 chars of composed instructions)
- `stack_hints`: list of detected artifact names (e.g. `pyproject.toml`, `package.json`) — filesystem existence only
- `health_flags`: list of short strings (e.g. `missing_clone`, `dirty`, `stale_head_30d`, `behind_remote`)

### `ContextPackResult`

- `ok`, `tier`, `workspace_name`
- `map` (when tier 0 or included)
- `cards` (when tier 1)
- `token_estimate` (rough char/4 estimate for agent budgeting)

## Service behavior

### `WorkspaceMapService.build`

Input: `MetagitConfig`, `config_path`, `workspace_root`, optional `SessionStore` for active project.

Uses `WorkspaceCatalogService.list_workspace(include_index=True)`. Maps index rows to `WorkspaceMapEntry`. Does **not** call git inspect per repo (keep T0 cheap).

### `RepoCardService.build_one` / `build_many`

Input: config, workspace_root, project_name + repo_name (or filter list).

Steps per repo:
1. Resolve index row from `WorkspaceIndexService`
2. If `exists`, call `inspect_repo_state(repo_path)`
3. Read manifest repo fields (tags, url, description)
4. Compose agent instruction excerpt via existing `agent_instructions` layering (repo scope only for card)
5. Scan stack hints: check up to 8 known filenames in repo root
6. Derive `health_flags` from git stats + index status

`build_many`: optional `project_name` filter; default all repos in workspace.

### `ContextPackService.pack`

- `tier=0`: return `WorkspaceMapResult` wrapped in `ContextPackResult`
- `tier=1`: return T0 map **plus** cards for scoped repos (default all; filter by `--project` / `--repo`)
- Enforce max cards default 50 (configurable) to prevent runaway token use

## CLI

```bash
metagit context pack --tier 0 [--json]
metagit context pack --tier 1 [--project NAME] [--repo NAME] [--json]
metagit context repo-card --project NAME --repo NAME [--json]
```

Register under `metagit context` group in `cli/main.py`.

## MCP tools

| Tool | Args | Returns |
|------|------|---------|
| `metagit_context_pack` | `tier` (0\|1), optional `project_name`, `repo_name` | `ContextPackResult` JSON |
| `metagit_repo_card` | `project_name`, `repo_name` | `RepoCardResult` JSON |

Add to `ToolRegistry._active_tools`, `_tool_schemas`, `_dispatch_tool`.

### MCP resource (optional v1)

- `metagit://workspace/context/t0` — cached-friendly T0 map via `ResourcePublisher`

## Prompt catalog

Add kind `context-pack` (scopes: workspace, project, repo):
- Instructs agent to call `metagit context pack --tier 0` at session start, escalate to tier 1 for repos in scope
- Template references CLI; MCP hosts use tool equivalent

## Error handling

- Missing workspace / inactive gate: MCP returns gate-appropriate errors (existing pattern)
- Unknown project/repo: `{ok: false, error: "not_found", ...}`
- Missing clone: card still returned with `exists: false`, `health_flags: ["missing_clone"]`

## Testing

| Test file | Coverage |
|-----------|----------|
| `tests/core/context/test_repo_card_service.py` | card fields, missing clone, stack hints |
| `tests/core/context/test_workspace_map_service.py` | T0 shape, project counts |
| `tests/core/context/test_context_pack_service.py` | tier 0/1 orchestration, filters |
| `tests/cli/commands/test_context.py` | CLI JSON output |
| `tests/core/mcp/test_runtime.py` | tool list + call for new tools |

Fixtures: temp workspace with small git repo (mirror `test_project_context.py` pattern).

## Success criteria

- `metagit context pack --tier 0 --json` returns valid JSON in <500ms on metagit-cli workspace
- `metagit context pack --tier 1 --project personal --repo metagit-cli --json` includes git branch + stack hints
- MCP tools visible when gate ACTIVE; return same JSON shape as CLI
- `task qa:prepush` passes
- MkDocs not required for v1 (no doc page unless trivial reference addition)

## Future phases (not in this spec)

- T2 digest (since last session)
- T2 upstream hint block on errors
- Objectives model + Web UI
- Context profiles for repomix

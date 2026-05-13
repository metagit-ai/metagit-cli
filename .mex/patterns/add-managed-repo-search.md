---
name: add-managed-repo-search
description: Extend or debug managed-only repo lookup across CLI, MCP, and the local JSON API.
triggers:
  - "managed repo search"
  - "metagit_repo_search"
  - "repos/search"
  - "ManagedRepoSearchService"
edges:
  - target: context/architecture.md
    condition: when changing how search flows connect CLI, MCP, and HTTP surfaces
  - target: context/mcp-runtime.md
    condition: when adjusting MCP tool schema or dispatch for managed repo search
  - target: patterns/add-mcp-tool.md
    condition: when only the MCP tool contract or registry changes
last_updated: 2026-05-12
---

# Add or change managed repo search

## Context
Managed repo search is **only** the repos declared under `workspace.projects[].repos` in `.metagit.yml`. It does not scan the filesystem for unmanaged clones. Shared logic lives in `src/metagit/core/project/search_service.py` (`ManagedRepoSearchService`) and index rows from `WorkspaceIndexService.build_index`.

## Steps
1. Confirm ranking/filter behavior in `ManagedRepoSearchService` (`search` / `resolve_one`) and adjust tests in `tests/test_project_search_service.py`.
2. **CLI:** `src/metagit/cli/commands/search.py` — keep thin; delegate to the service + `MetagitConfigManager`.
3. **MCP:** register in `tool_registry.py`, add `inputSchema` + dispatch in `runtime.py` (`metagit_repo_search`); extend `tests/core/mcp/test_runtime.py` (and integration if gating changes).
4. **HTTP API:** `src/metagit/core/api/server.py` — GET handlers only; keep JSON stable; add tests under `tests/api/`.
5. Regenerate schema if `.metagit.yml` / models affecting tags change (`task generate:schema`).

## Gotchas
- Workspace root for path resolution is the **directory containing** `.metagit.yml`, not the file path itself.
- `metagit_workspace_search` (MCP) searches **paths on disk** inside the workspace; `metagit_repo_search` searches **configured managed repos** — different semantics; do not merge without updating docs and clients.
- HTTP `409` on `/v1/repos/resolve` is expected for `ambiguous_match`; clients must handle it (e.g. `urllib` raises `HTTPError`).

## Verify
- [ ] `uv run pytest tests/test_project_search_service.py tests/cli/commands/test_search.py tests/core/mcp/test_runtime.py tests/api/test_repo_search_api.py -q`
- [ ] `task lint` and `task test` green after broader changes.

## Debug
- Empty MCP/API results: gate inactive, invalid config, or `workspace_root` mismatch vs repo `path:` entries.
- CLI vs API mismatch: compare `--definition` parent directory to API `--root`.

## Update Scaffold
- [ ] Update `docs/cli_reference.md` if flags or endpoints change.
- [ ] Update `.mex/ROUTER.md` if user-visible surfaces change materially.

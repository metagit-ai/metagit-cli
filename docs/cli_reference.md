# CLI Reference

This page contains the auto-generated documentation for the `metagit` command-line interface.

::: mkdocs-click
    :module: metagit.cli.main
    :command: cli
    :prog_name: metagit 

## MCP Command Notes

- Start MCP stdio runtime:
  - `metagit mcp serve`
- Start against a specific workspace root:
  - `metagit mcp serve --root /path/to/workspace`
- Print status snapshot and exit:
  - `metagit mcp serve --status-once`
- When the workspace gate is **active**, the tool **`metagit_repo_search`** searches only repos listed under `workspace.projects[].repos` in `.metagit.yml` (tags, sync status, resolved paths). Optional filters: `status[]`, `has_url`, `sync_enabled`, `sort` (`score`|`project`|`name`). Use query `*` for filter-only listing.
- **`metagit_workspace_search`** uses ripgrep when available (`repos`, `paths`, `exclude`, `context_lines`, `intent`, `include_paths`). Falls back to a bounded scanner if `rg` is not installed.
- **`metagit_workspace_sync`** batch-syncs repos (`repos: ["all"]` or selectors), with `only_if` (`any`|`missing`|`dirty`|`behind_origin`), `max_parallel`, and `dry_run`.
- **`metagit_cross_project_dependencies`** maps relationships from a `source_project` using `dependency_types` (`declared`, `imports`, `shared_config`, `url_match`, `ref`), `depth`, and per-repo GitNexus `graph_status` (`indexed`|`stale`|`missing`).
- **`metagit_workspace_health_check`** returns per-repo git/GitNexus signals, optional staleness metrics (`head_commit_age_days`, `merge_base_age_days` when `check_stale_branches`), tunable thresholds (`branch_head_warning_days`, `branch_head_critical_days`, `integration_stale_days`), and prioritized recommendations (`sync`, `analyze`, `clone`, `fix_config`, `review_branch_age`, `reconcile_integration`, …).
- **`metagit_workspace_semantic_search`** runs `npx gitnexus query -r <registry>` per selected repo (`query` required; optional `repos`, `task_context`, `goal`, `limit_per_repo`, `timeout_seconds`) for GitNexus-ranked processes.
- **`metagit_workspace_discover`** lists files by `intent` or `pattern` with optional `categorize` grouping (requires `intent` or `pattern`).
- **`metagit_project_template_apply`** previews or applies bundled templates from `src/metagit/data/templates/` (`dry_run` default; `confirm_apply` required for writes).
- **Resources (active gate):** `metagit://workspace/health`, `metagit://workspace/context` (active project session from `.metagit/sessions/`).
- **Project context (active gate):**
  - `metagit_project_context_switch` — set active workspace project; return repo branch/dirty summary, safe env exports (`METAGIT_*`), and restored session fields from `.metagit/sessions/<project>.json`.
  - `metagit_session_update` — persist `agent_notes`, `recent_repos`, and non-secret `env_overrides` before switching away.
  - `metagit_workspace_state_snapshot` — write a git-state manifest to `.metagit/snapshots/<id>.json` (not a file copy).
  - `metagit_workspace_state_restore` — reload snapshot metadata and optionally re-run context switch; does **not** reset git branches or uncommitted changes.

## Workspace configuration

Under `workspace.projects[].repos`, each repository entry may include a flat string-to-string `tags` map (for example `tier: "1"`). These tags are carried into the workspace index and into `metagit search` / `metagit find` for filtering.

## Managed repository search

- `metagit search QUERY` — list managed repositories from the workspace definition that match the query (name, URL substring, tag keys/values, project name). Only repos declared under `workspace.projects[].repos` are considered. Supports `--status` (repeatable) and `--sort score|project|name`.
- `metagit find QUERY` — alias for `metagit search`.
- `--definition PATH` — `.metagit.yml` to load (default: `.metagit.yml` in the current directory). The workspace root for resolving `path:` entries is the parent directory of that file.
- `--json` — print search results as JSON (matches include `match_reasons` and scores).
- `--path-only` — resolve to exactly one local directory (fails if there is no match or more than one match).
- `--tag key=value` — repeat to require matching tag values (all given pairs must match).
- `--project`, `--exact`, `--synced-only`, and `--limit` narrow or rank results further.

## Local JSON API (`metagit api`)

- `metagit api serve` — bind a `ThreadingHTTPServer` on `--host` / `--port` (default `127.0.0.1:7878`) under `--root` (directory containing `.metagit.yml`).
- `metagit api serve --status-once` — allocate a port (use `--port 0` for ephemeral), print `api_state=ready host=… port=…`, and exit (for tests and automation).
- `GET /v1/repos/search?q=…` — same managed-repo search as the CLI; optional query params: `project`, `exact=true|false`, `synced_only=true|false`, `limit`, repeat `tag=key=value`.
- `GET /v1/repos/resolve?q=…` — single-match resolution; HTTP `404` when not found, `409` when ambiguous (body includes `ManagedRepoResolveResult` JSON).
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
- **Shared coordination state:** export `METAGIT_STATE_URL` and optional `METAGIT_STATE_TOKEN` on the **MCP server process** before `metagit mcp serve` so objectives/handoffs/approvals/events use the remote ops backend. Verify via `resources/read` → `metagit://gate/status` (`state_backend` field). Skill: `metagit-sharing-state`.
- When the workspace gate is **active**, the tool **`metagit_repo_search`** searches only repos listed under `workspace.projects[].repos` in `.metagit.yml` (tags, sync status, resolved paths). Optional filters: `status[]`, `has_url`, `sync_enabled`, `sort` (`score`|`project`|`name`). Use query `*` for filter-only listing.
- **`metagit_workspace_search`** searches on-disk file contents (not manifest metadata). Uses ripgrep when available (`repos`, `paths`, `exclude`, `context_lines`, `intent`, `include_paths`). Always excludes scaffold paths (`node_modules`, `.venv`, etc.). Falls back to a bounded scanner if `rg` is not installed.
- **`metagit_workspace_grep_info`** returns `ripgrep_available`, `ripgrep_path`, `ripgrep_version`, and `search_backend` (`ripgrep` or `python_walk`). CLI equivalent: `metagit workspace grep info`.
- **`metagit_workspace_sync`** batch-syncs repos (`repos: ["all"]` or selectors), with `only_if` (`any`|`missing`|`dirty`|`behind_origin`), `max_parallel`, and `dry_run`.
- **`metagit_cross_project_dependencies`** maps relationships from a `source_project` using `dependency_types` (`declared`, `imports`, `shared_config`, `url_match`, `ref`), `depth`, and per-repo GitNexus `graph_status` (`indexed`|`stale`|`missing`).
- **`metagit_workspace_health_check`** returns per-repo git/GitNexus signals, optional staleness metrics (`head_commit_age_days`, `merge_base_age_days` when `check_stale_branches`), tunable thresholds (`branch_head_warning_days`, `branch_head_critical_days`, `integration_stale_days`), and prioritized recommendations (`sync`, `analyze`, `clone`, `fix_config`, `review_branch_age`, `reconcile_integration`, …).
- **`metagit_workspace_semantic_search`** runs `npx gitnexus query -r <registry>` per selected repo (`query` required; optional `repos`, `task_context`, `goal`, `limit_per_repo`, `timeout_seconds`) for GitNexus-ranked processes.
- **`metagit_workspace_discover`** lists files by `intent` or `pattern` with optional `categorize` grouping (requires `intent` or `pattern`).
- **`metagit_project_template_apply`** previews or applies bundled templates from `src/metagit/data/templates/` (`dry_run` default; `confirm_apply` required for writes).
- **Coordination (active gate):** `metagit_objective_list`, `metagit_objective_upsert`, `metagit_objective_edit`; `metagit_approval_request`, `metagit_approval_list`, `metagit_approval_resolve`; `metagit_handoff_list`, `metagit_handoff_create`, `metagit_handoff_claim`, `metagit_handoff_complete`; `metagit_events` (optional `since` ISO cursor; includes `source=acl` lifecycle rows). All respect `METAGIT_STATE_URL` when set on the MCP host.
- **ACL / Agent Coordination Layer (active gate):** `metagit_branch_allocate`, `metagit_branch_list`, `metagit_branch_release`; `metagit_lease_acquire`, `metagit_lease_renew`, `metagit_lease_release`, `metagit_lease_list`; `metagit_worktree_create`, `metagit_worktree_destroy`, `metagit_worktree_status`, `metagit_worktree_list`; `metagit_claim_declare`, `metagit_claim_check`, `metagit_claim_list`, `metagit_claim_release`. CLI: `metagit branch|lease|worktree|claim`. ACL branch leases are distinct from handoff claim TTL. See [agent-coordination.md](reference/agent-coordination.md).
- **Resources:** Start with `metagit://catalog`. Phase 1–4 URIs include `gate/status` (includes `state_backend` diagnostics), `workspace/map`, `session/meta`, `session/digest`, `objectives`, `approvals/pending`, `handoffs/open`, `events/recent`, `prompt/catalog`, dynamic `prompt/{scope}/{kind}`, `project/{project}/summary`, `repo/{project}/{repo}/card`, `workspace/config` (summary default), `workspace/repos/status?summary=1`, `workspace/health`, `workspace/context` (alias). Spec: [mcp-layered-resources-spec.md](reference/mcp-layered-resources-spec.md). Skills: `metagit-mcp-resources`, `metagit-sharing-state`.
- **Prompts capability:** `prompts/list` and `prompts/get` (names like `workspace/session-start`) mirror prompt resources.
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
- `GET /v2/workspace/grep?q=…` — content grep across managed repos (optional `project`, `repo`, `preset`, `intent`, `max_results`, `context_lines`, `include_paths`). CLI equivalent: `metagit workspace grep`.
- `GET /v2/workspace/grep/info` — ripgrep availability and search backend. CLI equivalent: `metagit workspace grep info`.

## Agent profile and campaigns

Structured manifest fields and CLI groups for multi-agent coordination. Full reference: [modality-feature-registry.md](reference/modality-feature-registry.md).

<!-- modality:agent_profile_apply -->
- **`metagit agent apply`** — materialize merged `agent_profile` blocks into vendor runtimes (`--project`, `--repo`, `--target`, `--dry-run`). See [agent-profile.md](reference/agent-profile.md).
- **`metagit agent profile show`** — print the effective merged profile for one repo.

<!-- modality:native_campaigns -->
- **`metagit campaign`** — `list`, `status`, `new`, `validate`, `set`, `expand` for cross-project campaign YAML under `workspace.campaigns_path` (default `_campaigns/`). See [campaigns.md](reference/campaigns.md).

<!-- modality:handoff_lease_heartbeat -->
<!-- modality:coordination_events_scope -->
<!-- modality:objective_mr_approval_binding -->
- **`metagit context handoff`** — queue operations including `claim --ttl`, `heartbeat`, and auto-release of expired claims.
- **`metagit context events`** — optional `--campaign` / `--objective` filters when polling workspace events (includes ACL `source=acl` rows).

<!-- modality:acl_branch -->
<!-- modality:acl_lease -->
<!-- modality:acl_worktree -->
<!-- modality:acl_claim -->
<!-- modality:acl_manifest -->
- **`metagit branch`** — allocate / release / cleanup / archive / list `agent/*` branches.
- **`metagit lease`** — acquire / renew / release / list ACL branch leases (not handoff claim TTL).
- **`metagit worktree`** — create / destroy / gc / status / list / manifest for isolated agent checkouts under `.worktrees/`.
- **`metagit claim`** — declare / check / list / release advisory file-path claims.
- Full ACL reference: [agent-coordination.md](reference/agent-coordination.md).

<!-- modality:dispatch_profile_capabilities -->
- **`metagit agent dispatch-plan`** — includes profile skill hints, suggested `profile_apply_command`, and `handoff.acl_commands` when project/repo are set.
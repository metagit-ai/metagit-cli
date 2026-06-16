# Changelog

## Unreleased



## [0.7.37] - 2026-06-16



_No commit notes generated._

## [0.7.36] - 2026-06-16



_No commit notes generated._

## [0.7.35] - 2026-06-16



_No commit notes generated._

## [0.7.34] - 2026-06-16



_No commit notes generated._

## [0.7.33] - 2026-06-16



_No commit notes generated._

## [0.7.32] - 2026-06-16



_No commit notes generated._

## [0.7.31] - 2026-06-16



_No commit notes generated._

## [0.7.30] - 2026-06-16



_No commit notes generated._

## [0.7.29] - 2026-06-16



_No commit notes generated._

## [0.7.28] - 2026-06-16



_No commit notes generated._

## [0.7.27] - 2026-06-16



_No commit notes generated._

## [0.7.26] - 2026-06-16



_No commit notes generated._

## [0.7.25] - 2026-06-16



_No commit notes generated._

## [0.7.24] - 2026-06-16



_No commit notes generated._

## [0.7.23] - 2026-06-16



_No commit notes generated._

## [0.7.22] - 2026-06-16



_No commit notes generated._

## [0.7.21] - 2026-06-16



_No commit notes generated._

## [0.7.20] - 2026-06-16



_No commit notes generated._

## [0.7.19] - 2026-06-16



_No commit notes generated._

## [0.7.18] - 2026-06-16



_No commit notes generated._

## [0.7.17] - 2026-06-16



_No commit notes generated._

## [0.7.16] - 2026-06-16



_No commit notes generated._

## [0.7.15] - 2026-06-16



_No commit notes generated._

## [0.7.14] - 2026-06-16



_No commit notes generated._

## [0.7.13] - 2026-06-16



_No commit notes generated._

## [0.7.12] - 2026-06-16



_No commit notes generated._

## [0.7.11] - 2026-06-16



_No commit notes generated._

## [0.7.10] - 2026-06-16



_No commit notes generated._

## [0.7.9] - 2026-06-16



_No commit notes generated._

## [0.7.8] - 2026-06-16



_No commit notes generated._

## [0.7.7] - 2026-06-16



_No commit notes generated._

## [0.7.6] - 2026-06-16



_No commit notes generated._

## [0.7.5] - 2026-06-16



_No commit notes generated._

## [0.7.4] - 2026-06-16



_No commit notes generated._

## [0.7.3] - 2026-06-16



_No commit notes generated._

## [0.7.2] - 2026-06-16



_No commit notes generated._

## [0.7.1] - 2026-06-16



_No commit notes generated._

## [0.7.0] - 2026-06-16



### Added

- **`metagit project source sync` enhancements:** include/ignore glob filters, `--ensure` / `--refresh-metadata` idempotency, provider topic enrichment into repo tags, default `namespaced` GitLab naming, `--json` agent output, `--sync` post-apply clone, MCP `metagit_project_source_sync`, `metagit workspace import` alias, declarative `workspace.projects[].sources[]` with `--from-manifest`, and approval-gated reconcile removals. **Web parity:** Config Studio `sources[]` editing, Workspace Console manifest sync (`POST /v3/ops/source-sync`), pending approvals panel, and shared `ApprovalResolveOrchestrator`.
- **Modality parity gate:** `scripts/modality-parity.yml` + `scripts/check_modality_parity.py` (wired into `task qa:prepush`) enforce declared CLI/MCP/web markers for operator-facing features.
- **`metagit version check`:** CLI and MCP `metagit_version_check` compare the installed package to the latest GitHub release (notes) and PyPI; available without an active workspace gate. Use `--json` or `include_notes: false` for agent-friendly output.
- **`metagit version upgrade`:** CLI and MCP `metagit_version_upgrade` detect the install channel (`uv tool`, `pip`, editable) and plan or run a self-update from PyPI. Defaults to dry-run; pass `--apply` or `apply: true` to execute. Refuses editable development installs.
- **Agent onboarding:** `llms.txt`, [docs/agents.md](docs/agents.md), and README/AGENTS.md sections so agents landing on the GitHub repo can install and use Metagit with minimal tokens (context packs, skills, MCP).
- **`metagit-agent-access` skill:** On-demand optimizer (script + subagent prompt) to scaffold `llms.txt`, `AGENTS.md`, and hidden README HTML agent blocks for any repository.
- **Context packs Phase 2:** tier **2** session digest (`SessionDigestService`), workspace **objectives** (CLI/MCP/Web), **approval queue** for mutating ops, and **repomix context profiles** (`bugfix-local`, `config-edit`, `cross-repo-impact`) via `metagit context repomix` and `task repomix:profile`.
- **Context packs Phase 1:** tier 0 workspace map and tier 1 repo cards via `metagit context pack`, MCP `metagit_context_pack` / `metagit_repo_card`, and prompt kind `context-pack`.
- **Repomix context profiles:** `src/metagit/data/context_profiles.yaml` bundles scoped globs; `RepomixProfileService` runs `repomix --include/--ignore` for a repository directory.
- Top-level **graph** block for manual cross-repo **relationships** (merged into cross-project dependency maps and `graph_export_payload()` for GitNexus-style exports).
- Per-project `dedupe.enabled` override on `workspace.projects[]` in `.metagit.yml` (overrides app-config `workspace.dedupe.enabled` for sync and layout under that project).
- `metagit prompt` kind `repo-enrich` (repo scope): CLI workflow to discover repo metadata (`metagit detect`, `project source sync`) and merge into the workspace manifest entry.
- Bundled skill `metagit-cli`: CLI-only shortcuts for agents, including every `metagit prompt` kind and common catalog/detect/sync commands (no MCP or HTTP API).
- `metagit prompt` command group: `list`, `workspace`, `project`, and `repo` subcommands emit built-in operational prompts or composed manifest `agent_instructions` (`--kind`, `--json`, `--text-only`).
- Top-level `agent_mode` in app config (default false), overridable via `METAGIT_AGENT_MODE`; disables interactive UIs (fuzzy finder, prompts, editor, prune confirms) across CLI when enabled.
- `metagit appconfig show` prints the full active configuration with `--format yaml|json|minimal-yaml` (includes `workspace.dedupe` and effective `agent_mode`).

### Added

- `metagit project sync --hydrate` materializes symlink mounts into full directory copies with per-file tqdm progress.

### Changed

- `workspace.dedupe.enabled` defaults to **false** in app config; enable in `metagit.config.yaml` or per-project `dedupe.enabled` in `.metagit.yml` when canonical checkouts are desired.
- `load_config()` applies environment variable overrides (same as `AppConfig.load()`), including `METAGIT_AGENT_MODE` and `METAGIT_WORKSPACE_DEDUPE_ENABLED`.
- `metagit config show` prints the source `.metagit.yml` by default (preserves your formatting); use `--normalized` for a readable model round-trip (`|` blocks, Unicode not escaped) or `--json` for agents.

### Added

- Workspace layout rename/move: rename projects and repos (manifest + sync folders), move repos across projects; CLI (`workspace project rename`, `workspace repo rename|move`), MCP (`metagit_workspace_project_rename`, `metagit_workspace_repo_rename`, `metagit_workspace_repo_move`), HTTP v2 (`POST /v2/projects/{name}/rename`, `/v2/repos/.../rename|move`). Supports `--dry-run`, `--manifest-only`, dedupe symlink mounts, and session file migration on project rename. See `docs/reference/workspace-layout-api.md`.
- Workspace catalog CRUD with JSON output: CLI (`metagit workspace list|project|repo`, `metagit project list --all`, `project add|remove`, `project repo list|remove`, `--json` on catalog commands), MCP tools (`metagit_workspace_list`, `metagit_workspace_projects_list`, `metagit_workspace_project_add|remove`, `metagit_workspace_repos_list`, `metagit_workspace_repo_add|remove`), and HTTP API v2 (`/v2/workspace`, `/v2/projects`, `/v2/repos`). Manifest-only repo/project removal; use `project repo prune` to delete unmanaged directories on disk.
- Docs: [Hermes agents and organization-wide IaC](docs/hermes-iac-workspace-guide.md) — illustrated controller/subagent workflow, manifest examples, and MCP tool map for platform IaC estates.
- Layered `agent_instructions` on `.metagit.yml` (file, workspace, project, repo/path); legacy `agent_prompt` accepted on load. `AgentInstructionsResolver` composes stacks for MCP project context (`instruction_layers`, `effective_agent_instructions`, per-repo `agent_instructions`).
- MCP `metagit_workspace_semantic_search` runs GitNexus `query` per managed repo (requires registry + index) for vector-ranked process results.
- MCP `metagit_workspace_health_check` includes branch age (`head_commit_age_days`, `merge_base_age_days`) when `check_stale_branches` is enabled, with thresholds `branch_head_warning_days` / `branch_head_critical_days` / `integration_stale_days` and summary counters for stale HEAD and integration drift.
- MCP Phase 3 workspace intelligence: `metagit_workspace_health_check`, `metagit_workspace_discover`, and `metagit_project_template_apply` (dry-run by default), plus resources `metagit://workspace/health` and `metagit://workspace/context`.
- MCP `metagit_cross_project_dependencies` to map declared, import-hint, and shared-config relationships between workspace projects with GitNexus index status per repo.
- MCP Phase 1 search/sync improvements: `metagit_repo_search` filters (`status`, `has_url`, `sync_enabled`, `sort`), `metagit_workspace_search` ripgrep-backed hits with `repos`/`paths`/`exclude`/`context_lines`/`intent`, and batch `metagit_workspace_sync` with `only_if` and `dry_run`.
- MCP project context tools: `metagit_project_context_switch`, `metagit_workspace_state_snapshot`, `metagit_workspace_state_restore`, and `metagit_session_update` for switching workspace projects with persisted session state under `.metagit/sessions/` and git-state snapshots under `.metagit/snapshots/`.
- Managed repository search across `.metagit.yml` workspace repos: CLI (`metagit search` / `metagit find`), MCP tool `metagit_repo_search`, and local JSON HTTP API (`metagit api serve` with `/v1/repos/search` and `/v1/repos/resolve`).
- `metagit project repo prune` to review and remove sync-folder directories not declared in `.metagit.yml` (with `--dry-run`, `--include-hidden`, and `--force` to skip prompts).
- `workspace.ui_ignore_hidden` in app config (default true) to hide dot-directories from the repo picker UI.

### Changed

- Removed redundant `config.version` from application config; use `metagit version` for the installed package. Legacy `version` keys in YAML are ignored on load. `api_version` remains for a future remote API contract (default empty; `METAGIT_API_VERSION` still applies).

### Fixed

- Workspace search: preset names that map to intent globs (e.g. `terraform`) now pass `**/*.tf` include globs to ripgrep; if ripgrep returns no hits while a `preset` or `intent` is set, the term-based filesystem fallback runs so Ubuntu/CI still gets matches when `rg` is installed but misbehaves or misparses.
- Workspace search fallback without `rg` matches preset-expanded terms (e.g. `preset=terraform`) instead of treating the composed `|` pattern as one literal string; fixes empty results when ripgrep is not installed.
- `task test` now runs `uv run pytest` so tests use the project virtualenv (fixes `ModuleNotFoundError: loguru` when `pytest` was not the venv binary).

## [0.2.2](https://github.com/metagit-ai/metagit-cli/compare/v0.2.1...v0.2.2) (2026-05-06)


### Bug Fixes

* revamp release workflow ([cafd6da](https://github.com/metagit-ai/metagit-cli/commit/cafd6dac4777c8528cc1c996bb8f1a394c40d53d))

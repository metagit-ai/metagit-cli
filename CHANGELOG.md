# Changelog

## Unreleased

### Added

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

- `task test` now runs `uv run pytest` so tests use the project virtualenv (fixes `ModuleNotFoundError: loguru` when `pytest` was not the venv binary).

## [0.2.2](https://github.com/metagit-ai/metagit-cli/compare/v0.2.1...v0.2.2) (2026-05-06)


### Bug Fixes

* revamp release workflow ([cafd6da](https://github.com/metagit-ai/metagit-cli/commit/cafd6dac4777c8528cc1c996bb8f1a394c40d53d))

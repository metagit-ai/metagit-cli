# Changelog

## Unreleased

### Added

- Managed repository search across `.metagit.yml` workspace repos: CLI (`metagit search` / `metagit find`), MCP tool `metagit_repo_search`, and local JSON HTTP API (`metagit api serve` with `/v1/repos/search` and `/v1/repos/resolve`).
- `metagit project repo prune` to review and remove sync-folder directories not declared in `.metagit.yml` (with `--dry-run` and `--include-hidden`).
- `workspace.ui_ignore_hidden` in app config (default true) to hide dot-directories from the repo picker UI.

### Changed

- Removed redundant `config.version` from application config; use `metagit version` for the installed package. Legacy `version` keys in YAML are ignored on load. `api_version` remains for a future remote API contract (default empty; `METAGIT_API_VERSION` still applies).

### Fixed

- `task test` now runs `uv run pytest` so tests use the project virtualenv (fixes `ModuleNotFoundError: loguru` when `pytest` was not the venv binary).

## [0.2.2](https://github.com/metagit-ai/metagit-cli/compare/v0.2.1...v0.2.2) (2026-05-06)


### Bug Fixes

* revamp release workflow ([cafd6da](https://github.com/metagit-ai/metagit-cli/commit/cafd6dac4777c8528cc1c996bb8f1a394c40d53d))

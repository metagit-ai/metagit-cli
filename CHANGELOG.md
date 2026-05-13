# Changelog

## Unreleased

### Added

- Managed repository search across `.metagit.yml` workspace repos: CLI (`metagit search` / `metagit find`), MCP tool `metagit_repo_search`, and local JSON HTTP API (`metagit api serve` with `/v1/repos/search` and `/v1/repos/resolve`).

### Fixed

- `task test` now runs `uv run pytest` so tests use the project virtualenv (fixes `ModuleNotFoundError: loguru` when `pytest` was not the venv binary).

## [0.2.2](https://github.com/metagit-ai/metagit-cli/compare/v0.2.1...v0.2.2) (2026-05-06)


### Bug Fixes

* revamp release workflow ([cafd6da](https://github.com/metagit-ai/metagit-cli/commit/cafd6dac4777c8528cc1c996bb8f1a394c40d53d))

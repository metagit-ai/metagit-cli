---
name: cli-tui-hub
description: Add or extend the Metagit Textual TUI hub and repo select shortcuts.
triggers:
  - "metagit tui"
  - "configuration wizard"
  - "select --repo"
edges:
  - target: patterns/add-cli-command.md
    condition: when adding new TUI-launched CLI workflows
last_updated: 2026-07-07
---

# CLI TUI Hub

## Context
The interactive CLI uses Textual (see `src/metagit/core/utils/fuzzyfinder.py`). The `metagit tui` command lives under `src/metagit/core/tui/` with a thin Click wrapper in `src/metagit/cli/commands/tui.py`.

## Steps
1. Add menu actions in `src/metagit/core/tui/catalog.py` with `argv` tails and `needs_manifest=True` when the command group accepts `-c .metagit.yml`.
2. Keep subprocess launching in `MetagitCommandRunner` — do not duplicate business logic in the TUI.
3. Extend `ConfigWizardService` for new app-config fields; keep save path on `save_config`.
4. For direct repo open without the picker, use `ProjectManager.resolve_selected_repo_path` via `execute_repo_select(..., repo_name=...)`.
5. Register top-level command in `src/metagit/cli/main.py`; reject `agent_mode`.

## Gotchas
- `ctx.obj["config_path"]` on `project` / `workspace` groups is the manifest path, not `metagit.config.yaml`.
- `--repo` bypasses fuzzy finder but still opens the editor unless `agent_mode` is active.
- TUI subprocesses unset `METAGIT_AGENT_MODE` so nested CLI calls remain interactive.
- Manifest flags differ by CLI group: `project`/`config` use `-c`; `workspace` uses `--config`; `search` uses trailing `--definition`.
- The TUI catalog omits context/agent prompt commands; use the CLI directly for those workflows.
- In-process repo picker (`run_repo_picker_session`) relies on `FuzzyFinder` running in a worker thread when the hub already has a Textual asyncio loop (`_run_textual_app` in `fuzzyfinder.py`).

## Verify
- [ ] `uv run metagit tui --help` and `uv run metagit project select --help` show new options.
- [ ] Tests under `tests/core/tui/` and `tests/cli/commands/test_project_select_repo.py` pass.
- [ ] `task qa:prepush` green after changes.

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
last_updated: 2026-07-14
---

# CLI TUI Hub

## Context
The interactive CLI uses Textual (see `src/metagit/core/utils/fuzzyfinder.py`). The `metagit tui` command lives under `src/metagit/core/tui/` with a thin Click wrapper in `src/metagit/cli/commands/tui.py`.

## Steps
1. Prefer the in-TUI **Select project → repository** flow (`navigation.py` + `ProjectSelectScreen` / `RepoSelectScreen`) for umbrella workspaces — no nested FuzzyFinder.
2. Add menu actions in `src/metagit/core/tui/catalog.py` with `argv` tails and `needs_manifest=True` when the command group accepts `-c .metagit.yml`.
3. Keep subprocess launching in `MetagitCommandRunner` — do not duplicate business logic in the TUI.
4. Extend `ConfigWizardService` for new app-config fields; keep save path on `save_config`.
5. For direct repo open without the picker, use `ProjectManager.resolve_selected_repo_path` via `execute_repo_select(..., repo_name=...)` or `open_selected_repo`.
6. Register top-level command in `src/metagit/cli/main.py`; reject `agent_mode`.

## Gotchas
- `ctx.obj["config_path"]` on `project` / `workspace` groups is the manifest path, not `metagit.config.yaml`.
- `--repo` bypasses fuzzy finder but still opens the editor unless `agent_mode` is active.
- TUI subprocesses unset `METAGIT_AGENT_MODE` so nested CLI calls remain interactive.
- Manifest flags differ by CLI group: `project`/`config` use `-c`; `workspace` uses `--config`; `search` uses trailing `--definition`.
- The TUI catalog omits context/agent prompt commands; use the CLI directly for those workflows.
- Legacy fuzzy picker (`run_repo_picker_session`) still suspends the hub and runs FuzzyFinder in a worker thread (`_run_textual_app`). Prefer the in-app project→repo screens for new UX.
- Quit bindings need `priority=True`; wrap `run_tui` against `KeyboardInterrupt`; catch `SuspendNotSupported` in interactive helpers.

## Verify
- [ ] `uv run metagit tui --help` and `uv run metagit project select --help` show new options.
- [ ] Tests under `tests/core/tui/` (including `test_tui_navigation.py`) and `tests/cli/commands/test_project_select_repo.py` pass.
- [ ] `task qa:prepush` green after changes.

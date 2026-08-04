---
name: metagit-nav
description: Human CLI shortcut for FuzzyFinder project then repo selection and editor open.
last_updated: 2026-08-03
---

# Metagit `nav` / `navigate` Design

**Date:** 2026-08-03  
**Status:** Approved (design)

## Summary

Add a top-level interactive CLI command `metagit nav` (alias `navigate`) that lets a human zoom into a workspace project, then pick a repository with the existing FuzzyFinder repo picker, then open the repo in the configured editor. This fills the gap where `metagit project select` requires `-p` / `default_project` / a single-project manifest before the repo picker runs.

## Problem

- `metagit project select` resolves the active project non-interactively (`resolve_active_project_name`). Multi-project workspaces abort without `-p`.
- `metagit tui` has project→repo ListViews, but that is a different interaction model (manifest lists, no filesystem FuzzyFinder preview).
- There is no dedicated CLI path that is: pick project (fuzzy) → pick repo (fuzzy) → open editor.

## Decisions

1. **Command surface:** Top-level `metagit nav` with Click alias `navigate`. Not nested under `project` or `workspace`.
2. **UX:** FuzzyFinder over project names, then existing `ProjectManager.select_repo()` FuzzyFinder (filesystem candidates + preview), then `open_editor`.
3. **Skips:** `-p` / `--project` skips project picker; sole project in manifest skips project picker; `--repo` skips repo picker and opens directly.
4. **Agent mode:** Reject with `UsageError` (same policy as `metagit tui`). No interactive FuzzyFinder under `METAGIT_AGENT_MODE`.
5. **Manifest flag:** `-c` / `--config` for `.metagit.yml` (consistent with `project` group), default `.metagit.yml`.
6. **Reuse:** Prefer composing `list_project_names` / `list_manifest_projects`, `project_manager_from_app`, `select_repo` / `resolve_selected_repo_path`, and `open_editor`. Add a small project FuzzyFinder helper; do not fork the TUI hub screens.
7. **Pattern deviation:** `.mex/patterns/cli-tui-hub.md` prefers in-TUI ListViews over nested FuzzyFinder for the hub. `nav` is an intentional dedicated Fuzzy→Fuzzy CLI shortcut, not an extension of `metagit tui`.

## CLI contract

```text
metagit nav|navigate [-c .metagit.yml] [-p PROJECT] [--repo REPO]
```

| Flag | Behavior |
|------|----------|
| `-c` / `--config` | Path to `.metagit.yml` |
| `-p` / `--project` | Project name; skip project FuzzyFinder; shell-complete via `complete_projects` |
| `--repo` | Repo name; skip repo FuzzyFinder; shell-complete via `complete_repos` |

### Flow

1. If `agent_mode`: raise `UsageError("Interactive navigation is disabled in agent mode")`.
2. Load app config + manifest; fail clearly if manifest missing/invalid.
3. Resolve project name:
   - Explicit `-p` → validate exists in manifest.
   - Else if exactly one project → use it.
   - Else → FuzzyFinder over project names; cancel → non-zero exit.
4. Set active project context equivalent to `project -p <name>` for the repo step.
5. Resolve repo:
   - `--repo` → `resolve_selected_repo_path`.
   - Else → `select_repo(...)` with workspace UI prefs from app config.
6. `open_editor(app_config.editor, path)`; log success/failure.

## Architecture

```text
nav.py (Click)
  → resolve project (flags | sole | FuzzyFinder)
  → ProjectManager.select_repo | resolve_selected_repo_path
  → open_editor
```

### Expected files

| Path | Role |
|------|------|
| `src/metagit/cli/commands/nav.py` | Click command + orchestration |
| `src/metagit/cli/main.py` | Register `nav` and alias `navigate` |
| Helper colocated with selection utils (e.g. under `metagit.core.project` or small function in `nav.py` if tiny) | Project-name FuzzyFinder |
| `tests/cli/commands/test_nav.py` | CLI tests |

## Error handling

- Unknown project / unknown repo → `ClickException`, non-zero exit.
- FuzzyFinder cancel / empty selection → non-zero exit with clear message.
- Editor failure → log error; exit non-zero when open fails.
- Missing sync mount for selected repo → same errors as `project select` today.

## Testing

- `--project` + `--repo` opens editor without FuzzyFinder (mirror `test_project_select_repo.py`).
- Agent mode rejects.
- Unknown project / repo exits non-zero.
- Single-project manifest skips project FuzzyFinder when `-p` omitted (monkeypatch FuzzyFinder to assert not called for projects).
- Multi-project without `-p` invokes project FuzzyFinder (stub return value).

## Non-goals

- Changing `metagit tui` project/repo screens.
- MCP tools.
- Context packs / objectives / env exports (see context-switch design).
- Replacing `metagit project select` or `metagit workspace select`.

## Related

- Sibling track: [2026-08-03-context-switch-design.md](2026-08-03-context-switch-design.md) (independent delivery).
- Pattern: `.mex/patterns/cli-tui-hub.md` (deviation noted above).
- Existing select path: `src/metagit/cli/commands/project_repo.py` (`execute_repo_select`).

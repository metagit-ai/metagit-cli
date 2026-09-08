# Metagit `nav --all` / `--print-path` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship flattened human `metagit nav --all` with repo-picker preview, `--unmanaged`, `--print-path`, plus MCP `metagit_repo_search` `path_only` and agent skill/docs parity.

**Architecture:** Extract shared FuzzyFinder preview assembly from `ProjectManager.select_repo`. Add `select_workspace_repos` for `project/repo` labels. `nav` stays a thin Click adapter. Agents do not use FuzzyFinder; they use `workspace repo list` + `search --path-only` / MCP `path_only`.

**Tech Stack:** Python 3, Click, FuzzyFinder (Textual), Pydantic, pytest, modality-parity.yml.

**Spec:** [2026-09-07-metagit-nav-all-print-path-design.md](../specs/2026-09-07-metagit-nav-all-print-path-design.md)

## Global Constraints

- `METAGIT_AGENT_MODE` still rejects all `nav` (including `--all` / `--print-path`).
- `--all` ignores `-p` / `--repo` (stderr warning).
- `--unmanaged` requires `--all`.
- `--print-path` stdout is only the absolute path + newline.
- MCP/web do not gain a FuzzyFinder. `path_only` is a flag on existing `metagit_repo_search`.
- 2-space vs 4-space: match the file being edited; Black formats Python.
- One feature commit at the end (operator requested commit/push/PR after complete).

## File map

| File | Responsibility |
|------|----------------|
| `src/metagit/core/project/manager.py` | Shared preview builder + `select_workspace_repos` |
| `src/metagit/cli/commands/nav.py` | `--all`, `--unmanaged`, `--print-path` |
| `src/metagit/core/mcp/runtime.py` | `path_only` schema + `resolve_one` dispatch |
| `tests/test_project_manager_select_repo.py` | Flattened picker unit tests |
| `tests/cli/commands/test_nav.py` | CLI flag tests |
| `tests/core/mcp/test_runtime.py` | MCP path_only tests |
| Skills / AGENTS.md / llms.txt / docs/agents.md / session-start / cli_reference / CHANGELOG / modality-parity.yml | Agent recipe + registry |

### Task 1: Shared picker + `select_workspace_repos`

**Files:** `src/metagit/core/project/manager.py`, `tests/test_project_manager_select_repo.py`

- [x] Extract scan/merge/target/finder helpers; keep `select_repo` behavior (gitignore, missing configured, unmanaged extras, preview metadata).
- [x] Add `select_workspace_repos(..., include_unmanaged=False)` returning selected path or None/Exception.
- [x] Tests: labels `project/repo`; unmanaged excluded by default; preview still has Managed/URL lines.

### Task 2: `nav` CLI flags

**Files:** `src/metagit/cli/commands/nav.py`, `tests/cli/commands/test_nav.py`

- [x] Flags and orchestration per spec.
- [x] Tests: `--print-path` no editor; `--all` ignores `-p/--repo`; `--unmanaged` without `--all` fails; agent mode still rejects.

### Task 3: MCP `path_only`

**Files:** `src/metagit/core/mcp/runtime.py`, `tests/core/mcp/test_runtime.py`

- [x] Schema boolean `path_only`; dispatch `resolve_one` with same filters as search (`synced_only` default False).
- [x] Tests: unique match `{ok, path, project, repo}`; ambiguous `{ok: false}`.

### Task 4: Docs, skills, prompts, modality, CHANGELOG

- [x] Agent navigate recipe (list + `--path-only` / MCP `path_only`); human `nav --all` documented separately.
- [x] `nav_flattened` + `managed_repo_search` registry rows; regenerate modality docs.
- [x] `.mex/ROUTER.md` + pattern notes.

### Task 5: QA, GitNexus, commit, PR, watch

- [x] `zsh ./scripts/prepush-gate.zsh` then `npx gitnexus analyze --skip-agents-md`.
- [x] Commit, push, `gh pr create`, `gh pr checks --watch`.

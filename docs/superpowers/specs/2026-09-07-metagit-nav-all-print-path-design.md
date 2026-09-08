---
name: metagit-nav-all-print-path
description: Flattened metagit nav TUI (--all, --unmanaged, --print-path) plus agent-fast navigation parity via catalog, search --path-only, and MCP resolve.
last_updated: 2026-09-07
---

# Metagit `nav --all` / `--print-path` Design

**Date:** 2026-09-07  
**Status:** Approved (spec)

Extends [2026-08-03-metagit-nav-design.md](2026-08-03-metagit-nav-design.md). Human shortcut remains FuzzyFinder. Agents **do not** use `nav`; they use the existing flattened catalog + path resolve, with MCP/docs/skills gaps closed so a low-skill agent can list every target and obtain one absolute path in one or two calls.

## Problem

- `metagit nav` is two FuzzyFinder steps. Humans want one list of every project/repo with the same right-hand metadata pane as the per-project repo picker.
- Humans also want “pick, then print the path” for `cd "$(metagit nav … --print-path)"` without launching an editor.
- Agents cannot run FuzzyFinder. `METAGIT_AGENT_MODE` already rejects `nav`. The flattened catalog already exists (`workspace repo list --json`, MCP `metagit_workspace_repos_list`), and CLI already has `metagit search QUERY --path-only`. Those facts are easy to miss: AGENTS.md still points humans at `nav` and agents at `search --json` without `--path-only`; MCP `metagit_repo_search` has no resolve/path-only flag (HTTP `/v1/repos/resolve` does).

## Decisions

1. **Human TUI:** `--all` is a single FuzzyFinder over workspace targets. Labels are `project/repo`. Preview uses the same `description` body as `ProjectManager.select_repo` (Name, Type, Git, MetaGit, managed summary, URL, tags, …). Preview on/off follows `workspace.ui_show_preview`.
2. **Managed by default:** `--all` lists catalogued repos only (including configured-but-not-synced rows, same as today’s picker). `--unmanaged` (only valid with `--all`) adds extra sync-folder directories across projects at opacity 0.5 with `Status: ❌ Unmanaged`.
3. **`--all` ignores `-p` / `--repo`:** always the full flattened picker. Emit a **stderr** warning that those flags are ignored. Two-step flow is unchanged when `--all` is omitted.
4. **`--print-path`:** FuzzyFinder still runs. On confirm, stdout is **only** the resolved absolute path plus a newline. No `open_editor`. Info/warnings go to stderr (do not `logger.info` the path on stdout). Works with two-step **and** `--all`. Cancel / error: non-zero, empty stdout.
5. **`--unmanaged` without `--all`:** `UsageError`.
6. **Agent mode:** `nav` still rejects (including `--print-path` and `--all`). Agents use the non-interactive surfaces below. Do not add FuzzyFinder to MCP or web.
7. **Shared builder:** extract filesystem + managed/unmanaged preview assembly from `select_repo` so `--all` and the per-project picker cannot drift (Approach 1 from brainstorming).
8. **Agent parity (where appropriate):** do **not** clone the TUI. Close the MCP/docs/skills gap so “list every managed target” and “resolve one path” are obvious one-liners. Reuse `WorkspaceCatalogService.list_repos` and `ManagedRepoSearchService.resolve_one`.

## CLI contract (human)

```text
metagit nav|navigate [-c FILE] [-p PROJECT] [--repo REPO]
                     [--all] [--unmanaged] [--print-path]
```

| Flag | Behavior |
|------|----------|
| *(none of the new flags)* | Existing: project picker → per-project repo picker (managed + unmanaged dirs) → editor |
| `--all` | One FuzzyFinder; ignores `-p` / `--repo` (stderr warning) |
| `--unmanaged` | With `--all` only: include unmanaged sync-folder dirs, dimmed |
| `--print-path` | After selection: print absolute path to stdout; skip editor |

Agent mode: `UsageError("Interactive navigation is disabled in agent mode")`.

## Agent navigation contract (non-TUI)

This is the agent equivalent of `--all` + `--print-path`. Prefer these over inventing `nav --json`.

| Human intent | Agent CLI | Agent MCP | HTTP (already exists) |
|--------------|-----------|-----------|------------------------|
| See every managed `project/repo` + path | `metagit workspace repo list -c .metagit.yml --json` | `metagit_workspace_repos_list` (optional `project_name`) | Existing catalog HTTP (`/v2` workspace list), not a new route |
| Fuzzy find by name/url | `metagit search "<q>" --json` | `metagit_repo_search` `{query, …}` | `GET /v1/repos/search` |
| One absolute path (fail if ambiguous) | `metagit search "<q>" --path-only` (`--project` / `--exact` as needed) | **`metagit_repo_search` + `path_only: true`** (new; same `resolve_one` as CLI) | `GET /v1/repos/resolve` |
| Full context switch (pack + env) | `metagit context switch P [R]` | `metagit_context_switch` | — |
| Unmanaged extra dirs | Human `--all --unmanaged` only | **Out of scope** (catalog/search are managed-only) | — |

MCP `path_only` response: JSON `{ "ok": true, "path": "<abs>", "project": "…", "repo": "…" }` or `{ "ok": false, "error": { "kind", "message", "matches" } }` matching `ManagedRepoResolveResult`. **One flag on `metagit_repo_search`**, not a new tool.

Invalid: `path_only` combined with treating a multi-match as success — `resolve_one` already errors on ambiguous/missing.

## Skills, prompts, docs (agent-easy)

Goal: a weak tool-using agent can copy two commands and succeed.

1. **`AGENTS.md`**, **`llms.txt`**, **`docs/agents.md`**, **`docs/agents-quickstart.md`:** add a “Navigate a target” row that lists the agent CLI (`workspace repo list --json` then `search … --path-only`). Keep `nav` labeled **human only**.
2. **`skills/metagit-cli/SKILL.md`** and **`skills/metagit-cli/metagit-cli/SKILL.md`:** short “Navigate (do not use `nav`)” section with the two commands and MCP names. `<!-- modality:… -->` anchors as required by the registry.
3. **`skills/metagit-workspace-scope/SKILL.md`:** under interactive/human, document `--all` / `--print-path`; under agent, document `repo list` + `search --path-only` (today it mentions `nav` without the agent substitute).
4. **`session-start` prompt** (`src/metagit/core/prompt/catalog.py`): one checklist line — list repos with `workspace repo list --json`; resolve a path with `search "<name>" --path-only` (never `metagit nav`).
5. **`docs/cli_reference.md`:** `--all`, `--unmanaged`, `--print-path` on `nav`; cross-link agent path resolve.
6. **CHANGELOG** Unreleased: human flags + MCP `path_only` + docs/skills.

## Architecture

```text
select_repo / select_workspace_repos
  → shared FuzzyFinderTarget builder (preview + opacity)
nav.py
  → if --all: select_workspace_repos(include_unmanaged=…)
  → else: existing project → select_repo | resolve_selected_repo_path
  → if --print-path: click.echo(path)   # stdout only
  → else: open_editor(...)

MCP metagit_repo_search
  → if path_only: ManagedRepoSearchService.resolve_one → JSON
  → else: existing search dump
```

Flattened picker iterates `list_project_names` (including `local` when present). Display `name` is `f"{project}/{repo}"`. Resolved open/print path is the same as `resolve_selected_repo_path` for managed rows, or `workspace/project/dirname` for unmanaged dirs.

### Expected files

| Path | Role |
|------|------|
| `src/metagit/core/project/manager.py` | Extract preview builder; add `select_workspace_repos` |
| `src/metagit/cli/commands/nav.py` | New flags; `--print-path` stdout; `--all` warning |
| `src/metagit/core/mcp/runtime.py` | `path_only` on `metagit_repo_search` schema + dispatch |
| `tests/cli/commands/test_nav.py` | `--all` / `--print-path` / `--unmanaged` / agent reject |
| `tests/core/mcp/test_runtime.py` | `path_only` success + ambiguous error |
| Skills / AGENTS.md / llms.txt / docs/agents.md / session-start | Agent recipe |
| `scripts/modality-parity.yml` | See parity section |

## Modality parity

| Surface | `nav --all` / `--print-path` | Agent list + resolve |
|---------|------------------------------|----------------------|
| CLI | Yes (`nav`) | Already: `workspace repo list`, `search --path-only` |
| MCP | **No** (human TUI exception) | Extend `metagit_repo_search` with `path_only`; list already exists |
| Web | **No** | Catalog/search already elsewhere; do not add a nav page |
| HTTP v1 | **No** | `/v1/repos/search` + `/v1/repos/resolve` already |
| Docs + skills | Yes | Yes — this is the agent UX |

Registry:

- New feature `nav_flattened`: CLI + documentation + skills markers for `--all` / `--print-path`. MCP/web omitted with a YAML comment: human FuzzyFinder; agents use managed repo search.
- Update the existing managed-repo-search feature markers so MCP schema contains `path_only` and skills/docs mention `--path-only`. If that feature is not in `scripts/modality-parity.yml` yet, add it in the same PR.

Run `task generate:modality-registry` as part of the change.

## Testing

**Human `nav`**

- `--all` stubs FuzzyFinder; items are `project/repo` for every managed repo; unmanaged absent unless `--unmanaged`.
- `--all -p x --repo y` still invokes flattened picker (not `resolve_selected_repo_path`); stderr contains ignored-flag warning.
- `--print-path` with stubbed selection: stdout is exactly `abspath\n`; `open_editor` not called.
- `--unmanaged` without `--all` → non-zero.
- Agent mode still rejects `--all` and `--print-path`.
- Existing `-p` + `--repo` editor tests remain.

**MCP**

- `metagit_repo_search` with `path_only: true` returns `ok` + `path` for a unique match.
- Ambiguous query returns `ok: false` and does not pick arbitrarily.

**Docs/skills**

- Modality marker check includes the new/updated rows.
- Prompt catalog test (if present) still matches session-start substring updates.

## Error handling

- Empty managed `--all` list: non-zero, clear message (no FuzzyFinder).
- Unmanaged-only extras with `--unmanaged` but zero managed + zero extras: same empty error.
- `--print-path` must not leak logger lines onto stdout (redirect logs or skip info logs on that path).
- MCP invalid `path_only` type → `-32602` `invalid_arguments`.

## Non-goals

- Changing `metagit tui` ListViews.
- Enabling `nav` under `METAGIT_AGENT_MODE`.
- JSON emit from `nav` (`--json`).
- MCP/web FuzzyFinder.
- Including unmanaged dirs in catalog/search.
- Replacing `context switch` (that is pack + env, not path print).

## Related

- [2026-08-03-metagit-nav-design.md](2026-08-03-metagit-nav-design.md)
- [2026-08-03-context-switch-design.md](2026-08-03-context-switch-design.md)
- Patterns: `.mex/patterns/cli-tui-hub.md`, `add-managed-repo-search.md`, `modality-parity.md`, `add-mcp-tool.md`
- CLI: `src/metagit/cli/commands/nav.py`, `search.py`
- Service: `ProjectManager.select_repo`, `ManagedRepoSearchService.resolve_one`, `WorkspaceCatalogService.list_repos`

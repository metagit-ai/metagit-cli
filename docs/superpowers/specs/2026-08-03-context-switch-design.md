---
name: context-switch
description: Agent CLI/MCP context switch composing ProjectContextService with pack, prompt, and objective bootstrap.
last_updated: 2026-08-03
---

# Metagit Context Switch Design

**Date:** 2026-08-03  
**Status:** Approved (design)

## Summary

Add `metagit context switch` (CLI), prompt kind `context-switch`, and MCP tool `metagit_context_switch` so agents can bootstrap into a project (optional repo) in one call — including shell-evalable env exports for `eval "$(metagit context switch …)"`. The feature **composes** existing `ProjectContextService.switch()`; it does not introduce a parallel switch system. Lean MCP `metagit_project_context_switch` remains unchanged for callers that only need session switch + env bundle.

## Problem

- Skills (`metagit-context-pack`, `metagit-workspace-scope`) document a multi-step workflow (pack + prompt + objectives) but lack a single entry point.
- MCP already exposes `metagit_project_context_switch` via `ProjectContextService`, but there is no CLI equivalent and no full bootstrap (tier-2 pack + switch prompt + objective) in one envelope.
- Hermes and other agents want `eval "$(metagit context switch <project>)"` to set env and receive pack/prompt context.

## Decisions

1. **Compose on existing switch:** Orchestrator calls `ProjectContextService.switch(...)` for session persistence and base env exports.
2. **Full bootstrap by default:** Tier-2 pack + `context-switch` prompt + auto objective, with opt-out flags.
3. **Keep existing env keys:** `METAGIT_WORKSPACE_ROOT`, `METAGIT_PROJECT`, `METAGIT_PROJECT_REPOS`, plus safe manifest `variables[]`. Do **not** rename to `METAGIT_CURRENT_*`.
4. **Shell bootstrap addition:** Emit `METAGIT_AGENT_MODE=true` in the shell-eval block (caller-facing).
5. **Tag-derived extras (convention, not schema break):** When present on project or primary repo tags:
   - `hermes_profile` → `METAGIT_HERMES_PROFILE`
   - `working_dir` → `METAGIT_WORKING_DIR`
   - `default_task_namespace` → `METAGIT_DEFAULT_TASK_NAMESPACE`
   - If `working_dir` tag absent: set `METAGIT_WORKING_DIR` from suggested cwd / primary repo sync path when available.
6. **Prompt kinds:** Add workspace kind `context-switch` (default for switch). Keep `session-start` for cold open. Standalone: `metagit prompt workspace -k context-switch --text-only`.
7. **MCP:** New `metagit_context_switch` → same orchestrator (JSON envelope). Keep `metagit_project_context_switch` lean.
8. **Output split:** Default stdout = shell-evalable `export` lines only (safe for `eval`). Pack JSON + prompt text on stderr. `--json` → full envelope on stdout.
9. **Independent of `nav`:** Separate PR/spec from human Fuzzy→Fuzzy navigation.

## CLI contract

```text
metagit context switch <project> [<repo>]
  [-c / --definition .metagit.yml]
  [--tier 0|1|2]                    # default 2
  [--no-pack]
  [--no-prompt]
  [--no-objective]
  [--prompt-kind context-switch|session-start]  # default context-switch
  [--json]
```

| Argument / flag | Behavior |
|-----------------|----------|
| `<project>` | Required; must exist in `workspace.projects[]` |
| `<repo>` | Optional; validated in project; passed as `primary_repo` to switch + pack scope |
| `--tier` | Pack tier when packing; default `2` |
| `--no-pack` / `--no-prompt` / `--no-objective` | Opt out of bootstrap pieces |
| `--prompt-kind` | Which prompt template to emit |
| `--json` | Structured `ContextSwitchResult` on stdout (no shell-eval) |

### Orchestrator flow

```text
ContextSwitchService.switch(...)
  1. Validate project (+ optional repo) in manifest
  2. ProjectContextService.switch(project, primary_repo=repo)
  3. Unless no_pack: ContextPackService.pack(tier, project, repo)
  4. Unless no_prompt: PromptService.emit(kind, scope=workspace)
  5. Unless no_objective: ObjectiveService.upsert_partial(
       id=ctx-<utc-timestamp>,
       title="Context: <P>" or "Context: <P>/<R>",
       repos=[resolved path(s)],
       status=in_progress,
     )
  6. Merge tag-derived env into export map
  7. Return ContextSwitchResult envelope
```

Mirror `SessionBeginService` composition style: thin orchestrator, no duplicated pack/prompt/objective logic.

## Envelope model (`ContextSwitchResult`)

Pydantic model (names indicative):

| Field | Type | Notes |
|-------|------|-------|
| `ok` | bool | False on validation / switch failure |
| `error` | str \| None | Machine-readable error code when not ok |
| `project_name` | str | |
| `repo_name` | str \| None | |
| `switch` | ProjectContextBundle \| dict | From `ProjectContextService` |
| `pack` | ContextPackResult \| None | |
| `prompt` | str \| None | Emitted prompt text |
| `prompt_kind` | str \| None | |
| `objective_id` | str \| None | |
| `env` | dict[str, str] | Final export map (base + agent mode + tags) |
| `warnings` | list[str] | Soft failures (e.g. prompt unavailable) |

## Shell-eval output (default)

Stdout example:

```bash
export METAGIT_AGENT_MODE=true
export METAGIT_WORKSPACE_ROOT="/path/to/sync"
export METAGIT_PROJECT="attune"
export METAGIT_PROJECT_REPOS="/path/to/attune"
export METAGIT_WORKING_DIR="/path/to/attune"
export METAGIT_HERMES_PROFILE="attune"
```

Stderr carries human/agent-readable pack JSON and prompt (or a short pointer). Agents that need structured data use `--json` or MCP.

Values must be shell-escaped (`shlex.quote`) so paths with spaces are safe.

## Prompt kind `context-switch`

Workspace-scoped checklist distinct from cold `session-start`:

- Confirm env exports (`METAGIT_PROJECT`, working dir, hermes profile if set).
- Treat the attached/available tier pack as current scope; do not re-run cold session-start blindly.
- Note active objective id when present.
- Prefer scoped sync / search within the switched project.
- Point to lean MCP `metagit_project_context_switch` only when pack/objective are not needed.

## MCP tool `metagit_context_switch`

| Arg | Required | Notes |
|-----|----------|-------|
| `project_name` | yes | |
| `repo_name` | no | |
| `tier` | no | default 2 |
| `include_pack` | no | default true |
| `include_prompt` | no | default true |
| `include_objective` | no | default true |
| `prompt_kind` | no | `context-switch` \| `session-start` |

Returns JSON of `ContextSwitchResult.model_dump(mode="json")`.

Registration: schema in runtime, name in `ToolRegistry._active_tools`, dispatch branch, tests in `tests/core/mcp/test_runtime.py`. Follow `.mex/patterns/add-mcp-tool.md`.

## Tag convention docs

Document (no hard schema change) that project/repo `tags` may include:

| Tag key | Env export | Purpose |
|---------|------------|---------|
| `hermes_profile` | `METAGIT_HERMES_PROFILE` | Hermes profile name |
| `working_dir` | `METAGIT_WORKING_DIR` | Preferred cwd override |
| `default_task_namespace` | `METAGIT_DEFAULT_TASK_NAMESPACE` | Task graph namespace hint |

Repo tags win over project tags when both set for the same key and a primary repo is selected; otherwise project tags apply.

## Surfaces / modality

- CLI: `metagit context switch`
- Prompt: `context-switch` kind
- MCP: `metagit_context_switch`
- Skills: update `metagit-context-pack`, `metagit-workspace-scope`
- Modality id: `context_switch` in `scripts/modality-parity.yml` with `<!-- modality:context_switch -->` anchors
- Docs: reference page or section for context switch + tag conventions

## Error handling

- Unknown project → `ok=false`, error `project_not_found` (CLI: ClickException).
- Unknown repo → `ok=false`, error `repo_not_found`.
- Switch failure → propagate `ProjectContextBundle` error.
- Pack / prompt soft failures → populate `warnings`, still return env + switch when possible.
- Objective upsert failure → warning or hard fail? **Hard fail** only if objective was requested and upsert raises; otherwise include warning and continue when store is temporarily unavailable — prefer **hard fail** for consistency with `objective set` CLI (raise to caller).

Clarified: objective upsert errors are hard failures when `--no-objective` is not set.

## Testing

- Service unit tests: validation, opt-outs, env merge (tags + `METAGIT_AGENT_MODE`), objective id shape.
- CLI: `--json` envelope; default stdout is only `export` lines; unknown project exits non-zero.
- MCP: tool listed ACTIVE; call returns envelope with pack/prompt/objective_id.
- Prompt catalog: `context-switch` allowed for workspace; `metagit prompt workspace -k context-switch` works.
- Modality parity markers present.

## Non-goals

- Renaming existing env vars to `METAGIT_CURRENT_*`.
- Removing or changing lean `metagit_project_context_switch`.
- Changing `metagit context session begin` semantics (related but separate cold-start path).
- Auto-install Hermes skills (already works via `metagit skills install --target hermes`).
- Human `metagit nav` (sibling track).

## Related

- Sibling track: [2026-08-03-metagit-nav-design.md](2026-08-03-metagit-nav-design.md)
- Existing: `ProjectContextService`, `SessionBeginService`, `ContextPackService`, `ObjectiveService`, `PromptService`
- Patterns: `.mex/patterns/add-mcp-tool.md`, `.mex/patterns/mcp-project-context.md`, `.mex/patterns/modality-feature-registry.md`

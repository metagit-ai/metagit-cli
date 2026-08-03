---
name: context-switch
description: Implement or extend metagit context switch CLI/MCP bootstrap (compose ProjectContextService + pack + prompt + objective).
triggers:
  - "context switch"
  - "metagit context switch"
  - "metagit_context_switch"
  - "context-switch prompt"
edges:
  - target: patterns/mcp-project-context.md
    condition: when changing lean ProjectContextService or session store
  - target: patterns/add-prompt-catalog-kind.md
    condition: when editing prompt kinds/templates
  - target: patterns/add-mcp-tool.md
    condition: when adding MCP schema/dispatch
  - target: patterns/modality-feature-registry.md
    condition: when registering modality context_switch
last_updated: 2026-08-03
---

# Context Switch Bootstrap

## Context

Design: `docs/superpowers/specs/2026-08-03-context-switch-design.md`  
Plan: `docs/superpowers/plans/2026-08-03-context-switch.md`

Full bootstrap composes existing services; do not fork session persistence. Sibling human track `metagit nav` is independent (`docs/superpowers/plans/2026-08-03-metagit-nav.md`).

## Steps

1. Keep lean MCP `metagit_project_context_switch` unchanged; put pack/prompt/objective in `ContextSwitchService`.
2. Default CLI stdout = shell `export` lines only (`shlex.quote`); pack/prompt on stderr; `--json` for agents.
3. Preserve env keys `METAGIT_WORKSPACE_ROOT` / `METAGIT_PROJECT` / `METAGIT_PROJECT_REPOS`; add `METAGIT_AGENT_MODE=true` and tag-derived extras.
4. Prompt kind `context-switch` is workspace-scoped; cold start stays `session-start`.
5. Register modality `context_switch` with docs/skills markers; run `task skills:sync` after skill edits.

## Gotchas

- Session root vs sync root: match `SessionBeginService` / existing MCP project-context dispatch — do not invent a third root rule.
- Objective upsert failures are hard failures when objectives are included.
- Tag conventions (`hermes_profile`, `working_dir`, `default_task_namespace`) are documentation + export only — no schema break.

## Verify

- [ ] `uv run pytest tests/core/context/test_context_switch_service.py tests/cli/commands/test_context*.py -q`
- [ ] MCP tool listed and covered in `tests/core/mcp/test_runtime.py`
- [ ] `task qa:prepush` then `task gitnexus:analyze`

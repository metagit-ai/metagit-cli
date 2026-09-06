---
name: component-compile
description: Optional --component/--depth on context compile (RFC-0029).
triggers:
  - "context compile --component"
  - "component_graph"
  - "RFC-0029"
  - "CompiledContext.component"
edges:
  - target: "component-resolution.md"
    condition: when ComponentResolver.get or three-segment id agreement is involved
  - target: "component-graph.md"
    condition: when neighborhood depth or ComponentGraphService is involved
  - target: "component-agent-profile.md"
    condition: when attaching effective_profile from AgentProfileService
  - target: "add-cli-command.md"
    condition: when changing metagit context compile flags
  - target: "add-mcp-tool.md"
    condition: when changing metagit_context_compile schema
last_updated: 2026-09-06
---

# Component-scoped context compile (RFC-0029)

## Context

Design: `docs/superpowers/specs/2026-09-06-rfc-0029-component-compile-design.md`.
Depends on RFC-0027 `ComponentResolver` and RFC-0028 `ComponentGraphService`.
Profile merge (decisions 3–4) is already in `AgentProfileService.effective_profile`.

Service: `src/metagit/core/context/compiler.py`.
Models: `CompiledContextInputs.component` / `.depth`; `CompiledContext.component` / `.component_graph` / `.effective_profile`.
CLI: `src/metagit/cli/commands/context.py` (`compile_cmd`).
MCP: `metagit_context_compile` in `runtime.py`.
Tests: `tests/core/context/test_compiler.py`, `tests/cli/commands/test_context.py`, `tests/core/mcp/test_task_tools.py`.

Do not invent a second compile modality id — extend `context_compile`.

## Steps

1. Keep `--project` and `--repo` required. `--component` is optional; `--depth` defaults to 0 and is ignored when component is omitted.
2. After `_resolve_scope`, resolve with `ComponentResolver.get(config, identity, project=project_name, repo=repo_name)`.
3. A three-segment id must agree with the resolved project/repo or compile returns an Exception.
4. Unknown component is an Exception (not a repo-wide fallback). Do not use `effective_profile is None` as the unknown-component signal.
5. When component is set, call `ComponentGraphService().neighborhood(...)` at the given depth and store the dict on `CompiledContext.component_graph`.
6. `CompiledContext.component` is `resolved_component_payload(row)`.
7. Optional `effective_profile` is `AgentProfileService(...).effective_profile(..., component_name=row.name).model_dump(mode="json")` or None when no profile exists.
8. Pack stays project/repo scoped. Do not shrink cards to one path.

## Gotchas

- Import `catalog` / `resolve` / `graph` from their modules, not `metagit.core.component.__init__`.
- Import `AgentProfileService` from `metagit.core.agent.profile_service`.
- `ComponentGraphService` already caps depth at 5.
- CLI compile tests that already use CliRunner can stay on CliRunner; component CLI tests use subprocess because of UnifiedLogger races.

## Verify

- [ ] `uv run pytest tests/core/context/test_compiler.py tests/cli/commands/test_context.py::test_context_compile_json tests/cli/commands/test_context.py::test_context_compile_json_component_neighborhood tests/core/mcp/test_task_tools.py::test_context_compile_schema_includes_component_and_depth`
- [ ] Compile without `--component` leaves component / component_graph / effective_profile None and inputs.depth 0
- [ ] `task qa:prepush` (or `zsh ./scripts/prepush-gate.zsh` if `task` mise shims fail)

## Update Scaffold

- [ ] `.mex/ROUTER.md` project state
- [ ] `docs/reference/context-compiler.md` and `docs/concepts/components.md`

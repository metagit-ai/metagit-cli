# RFC-0029: Component-Scoped Context Compile — Design

**Status:** Implemented
**Date:** 2026-09-06
**Series:** [Component Context Graph index](2026-09-06-rfc-0026-component-context-graph-index.md)
**Depends on:** [RFC-0028](2026-09-06-rfc-0028-component-graph-design.md)
**Plan:** [2026-09-06-rfc-0028-0032-remaining-series.md](../plans/2026-09-06-rfc-0028-0032-remaining-series.md)

## Summary

Extend `metagit context compile` with optional `--component` and `--depth`. Merge `agent_profile` workspace → project → repo → component. Attach a bounded component neighborhood to the compiled artifact. Do not add detect, claims, or derived working sets.

## Goals

- Optional component scope on compile (CLI, MCP).
- Inherited effective profile including the component layer.
- Graph expansion via RFC-0028 `ComponentGraphService.neighborhood`.
- Minimum sufficient context: default depth `0`.

## Non-Goals

- LLM relevance ranking
- New `metagit context derive` command (RFC-0032 uses existing derived projects)
- Changing required `--project` / `--repo`
- SPA compile UI

## Decisions (locked)

1. **`--project` and `--repo` stay required.** `--component` is optional extra scope (bare name or unique; three-segment id must agree with project/repo or compile returns an error).
2. **`--depth` default 0** (origin component only). Cap 5. Ignored when `--component` is omitted.
3. **Profile merge** adds layer `scope="component"` after repo when the component has `agent_profile`. `inherit: false` on the component replaces parents, same as repo today.
4. **`EffectiveAgentProfile`** gains optional `component_name: str | None = None`.
5. **`CompiledContextInputs`** gains `component: str | None = None` and `depth: int = 0`.
6. **`CompiledContext`** gains optional `component` (resolver payload) and `component_graph` (neighborhood dict or None).
7. **Pack remains project/repo.** Do not silently shrink repo cards to one path in this slice; the component payload + graph is the extra section. Repomix `--profile` flag is unchanged (still a pack profile name).
8. **Unknown component** is a compile error (`Exception` / CLI exit 1), not a repo-wide fallback.
9. **Modality:** extend existing `context_compile` markers; do not invent a second compile feature id.
10. **Objective/task** still override project/repo via `_resolve_scope`. After that override, apply `--component` against the resolved project/repo.

## CLI

```text
metagit context compile --project P --repo R [--component NAME] [--depth N] ...
```

MCP `metagit_context_compile` optional `component`, `depth`.

## Tests

- Compile without `--component` unchanged (no `component` / `component_graph` keys populated).
- `--component web` writes payload for `platform/core/web` on the native fixture.
- `--depth 1` includes `api` neighbor.
- Component `agent_profile.skills` appear in `effective_profile` after repo skills when inherit is true.
- Unknown component fails.
- Three-segment id that disagrees with `--project`/`--repo` fails.

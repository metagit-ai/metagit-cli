---
name: component-graph
description: GraphEndpoint.component, catalog validation, component: ids, and ComponentGraphService.neighborhood (RFC-0028).
triggers:
  - "RFC-0028"
  - "GraphEndpoint.component"
  - "component graph"
  - "ComponentGraphService"
  - "neighborhood"
  - "resolve_graph_endpoint_id"
edges:
  - target: "component-model.md"
    condition: when catalog identity or repos[].components[] is involved
  - target: "component-resolution.md"
    condition: when looking up a component via ComponentResolver.get or resolve
  - target: "graph-suggest-maintain.md"
    condition: when graph.relationships validation or durable fields change
  - target: "../context/conventions.md"
    condition: when writing or reviewing config/graph code
last_updated: 2026-09-06
---

# Component graph (RFC-0028)

## Context

Design: `docs/superpowers/specs/2026-09-06-rfc-0028-component-graph-design.md`.
Plan: `docs/superpowers/plans/2026-09-06-rfc-0028-0032-remaining-series.md`.
Depends on RFC-0026 catalog and RFC-0027 `ComponentResolver`.

Endpoint model: `src/metagit/core/config/graph_models.py` (`GraphEndpoint.component`).
Validation: `src/metagit/core/config/graph_validation.py`.
Resolver: `src/metagit/core/config/graph_resolver.py`.
Neighborhood: `src/metagit/core/component/graph.py` (`ComponentGraphService`).
Tests: `tests/core/config/test_graph_validation.py`, `tests/core/config/test_graph_resolver.py`, `tests/core/component/test_graph.py`.

CLI, MCP, web, and Cypher kind=`component` are later RFC-0028 tasks. Do not import `catalog`, `resolve`, or `graph` from `metagit.core.component.__init__`.

## Steps

1. Keep `extra="forbid"` on `GraphEndpoint`. `component` is optional; `path` stays an optional annotation.
2. In `_validate_endpoint`, pass `config: MetagitConfig`. If `component` is non-empty after strip, require both `project` and `repo`, then `ComponentResolver().get(config, f"{project}/{repo}/{component}")`.
3. Import `from metagit.core.component.resolve import ComponentResolver` (not the package `__init__`).
4. `None` from `get` → unknown component error. `ValueError` → include the exception message in issues.
5. Resolver: when `component` is set, return `component:{project}/{repo}/{component}` without consulting index `rows`. Missing project or repo → `None`. Do not use `path` in the id.
6. When `component` is unset, keep `repo:` / `project:` logic.
7. Neighborhood lives only in `ComponentGraphService.neighborhood`. Import `from metagit.core.component.resolve import ComponentResolver, resolved_component_payload` and `ComponentRef` from `metagit.core.component.models`.
8. Build edges from `graph.relationships` (`origin: declared`) and `Component.depends_on` (`type` and `origin` both `depends_on`). Duplicate from/to/type: `declared` wins. Edge field is `from`, not `from_id`.
9. Declared endpoint with `component` uses `get`. Path without component uses `ComponentResolver.resolve(..., project=, repo=)` only when both are set. Repo-only / unresolved path edges are excluded.
10. `depends_on` bare string is the same project/repo name. `ComponentRef` uses its fields, defaulting missing project/repo to the source row.
11. Walk is BFS. `direction` `out|in|both`. `depth` default 1; `0` origin only; cap 5; negative `ValueError`. Nodes: origin first, then BFS, then stable id sort within a depth. Unknown identity → `None`. Ambiguous bare name → `ValueError` from `get`.

## Gotchas

- Path-only and repo-only endpoints remain valid on the workspace graph; do not require `component`. They are not neighborhood nodes unless they resolve to a catalogued component.
- A project-only endpoint that also sets `component` is now invalid (needs repo too).
- Resolver does not consult `project_names` or `rows` on the component path — validation already rejected unknown catalog identities.
- Native fixture in `tests/core/component/test_resolve.py` (`_native()`) does **not** set `depends_on`. Graph tests must copy it and set `web.depends_on = ["api"]`.
- New `src/metagit/core/component/` files use 4-space indent and `#!/usr/bin/env python`.

## Verify

- [ ] `uv run pytest tests/core/config/test_graph_validation.py tests/core/config/test_graph_resolver.py tests/core/component/test_graph.py`
- [ ] `task generate:schema` after model field changes
- [ ] `task qa:prepush`

## Update Scaffold

- [ ] `.mex/ROUTER.md` project state
- [ ] `docs/concepts/components.md` when operator-facing graph CLI ships

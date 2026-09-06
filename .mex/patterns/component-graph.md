---
name: component-graph
description: GraphEndpoint.component, catalog validation, and component: resolver ids (RFC-0028).
triggers:
  - "RFC-0028"
  - "GraphEndpoint.component"
  - "component graph"
  - "resolve_graph_endpoint_id"
edges:
  - target: "component-model.md"
    condition: when catalog identity or repos[].components[] is involved
  - target: "component-resolution.md"
    condition: when looking up a component via ComponentResolver.get
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
Tests: `tests/core/config/test_graph_validation.py`, `tests/core/config/test_graph_resolver.py`.

Neighborhood walk, CLI, MCP, web, and Cypher kind=`component` are later RFC-0028 tasks — do not import `ComponentGraphService` from `metagit.core.component.__init__`.

## Steps

1. Keep `extra="forbid"` on `GraphEndpoint`. `component` is optional; `path` stays an optional annotation.
2. In `_validate_endpoint`, pass `config: MetagitConfig`. If `component` is non-empty after strip, require both `project` and `repo`, then `ComponentResolver().get(config, f"{project}/{repo}/{component}")`.
3. Import `from metagit.core.component.resolve import ComponentResolver` (not the package `__init__`).
4. `None` from `get` → unknown component error. `ValueError` → include the exception message in issues.
5. Resolver: when `component` is set, return `component:{project}/{repo}/{component}` without consulting index `rows`. Missing project or repo → `None`. Do not use `path` in the id.
6. When `component` is unset, keep `repo:` / `project:` logic.

## Gotchas

- Path-only and repo-only endpoints remain valid; do not require `component`.
- A project-only endpoint that also sets `component` is now invalid (needs repo too).
- Resolver does not consult `project_names` or `rows` on the component path — validation already rejected unknown catalog identities.
- Native fixture pattern lives in `tests/core/component/test_resolve.py` (`_native()`).

## Verify

- [ ] `uv run pytest tests/core/config/test_graph_validation.py tests/core/config/test_graph_resolver.py`
- [ ] `task generate:schema` after model field changes
- [ ] `task qa:prepush`

## Update Scaffold

- [ ] `.mex/ROUTER.md` project state
- [ ] `docs/concepts/components.md` when operator-facing graph CLI ships

# RFC-0028: Component Graph Integration — Design

**Status:** Approved for implementation
**Date:** 2026-09-06
**Series:** [Component Context Graph index](2026-09-06-rfc-0026-component-context-graph-index.md)
**Depends on:** [RFC-0026](2026-09-06-rfc-0026-component-model-design.md), [RFC-0027](2026-09-06-rfc-0027-component-resolution-design.md)
**Plan:** [2026-09-06-rfc-0028-0032-remaining-series.md](../plans/2026-09-06-rfc-0028-0032-remaining-series.md)

## Summary

Extend existing `graph.relationships` endpoints with optional `component`, resolve those endpoints to `component:{project}/{repo}/{name}` node ids, and add a depth-limited neighborhood walk over catalogued components. Do not add compile, claims, detect, or derived working sets.

## Goals

- Optional `GraphEndpoint.component`.
- Validate component endpoints against the catalog when `component` is set.
- Keep path-only and repo-only endpoints valid.
- Neighborhood walk combining durable `graph.relationships` and same-catalog `Component.depends_on`.
- `metagit component graph`, MCP `metagit_component_graph`, GET `/v3/ops/components/graph`.

## Non-Goals

- `context compile --component` (RFC-0029)
- Claims / ownership (RFC-0030)
- Detect / init (RFC-0031)
- Derived working sets (RFC-0032)
- LLM ranking, SPA graph page rewrite
- Replacing `metagit config graph export|suggest`

## Decisions (locked)

1. **Extend `GraphEndpoint`.** Add `component: str | None`. `extra` stays `forbid`. `path` remains optional annotation.
2. **Component requires project + repo.** `config validate` errors if `component` is set without both. Unknown catalog identity is an error.
3. **Resolver id** is `component:{project}/{repo}/{component}` when `component` is set; otherwise existing `repo:` / `project:` rules. `path` still does not change repo/project ids.
4. **Neighborhood edges** come from two origins:
   - `declared`: `graph.relationships` where both ends resolve to catalogued components (explicit `component`, or `path` longest-match via `ComponentResolver` inside the endpoint’s project/repo).
   - `depends_on`: `Component.depends_on` (bare name = same project/repo; `ComponentRef` uses its fields, defaulting missing project/repo to the source row).
5. **Repo-only / project-only edges** stay in the workspace graph; they are **not** in the component neighborhood.
6. **Walk** is BFS. `direction` is `out` (default), `in`, or `both`. `depth` default `1`; `0` is origin only. Cap at `5`.
7. **Type filter** optional; default all types. `depends_on` synthetic edges use type `depends_on`.
8. **One service:** `ComponentGraphService` in `src/metagit/core/component/graph.py`. Do not import it from `metagit.core.component.__init__`.
9. **Cypher:** `GraphCypherNode.kind` adds `"component"`; optional `component` property. Manual edges that resolve to component ids emit those nodes plus a `contains` structure edge from the parent repo node when structure export is on.
10. **Modality id** `component_graph`.
11. **CLI tests** for `component graph` use subprocess, not CliRunner.

## Neighborhood JSON

```json
{
  "origin": { "id": "platform/core/web", "project": "platform", "repo": "core", "name": "web", "path": "apps/web", "source": "native", "kind": "application", "spec": {} },
  "depth": 1,
  "direction": "out",
  "nodes": [ /* origin plus neighbors, catalog payloads */ ],
  "edges": [
    { "from": "platform/core/web", "to": "platform/core/api", "type": "depends_on", "origin": "depends_on" }
  ]
}
```

Node list is origin first, then BFS order, then stable id sort within a depth. Duplicate edges (same from/to/type) collapse; `declared` wins over `depends_on`.

Unknown identity → `ValueError`. Missing component → `None` at service for `get`-style; CLI/MCP map to not-found.

## CLI / MCP / Web

```text
metagit component graph <identity> [--project] [--repo] [--depth 1] [--direction out|in|both] [--json] [-c]
```

MCP `metagit_component_graph`: required `component`; optional `project`, `repo`, `depth`, `direction`.

Web: register **`GET /v3/ops/components/graph` before** `/v3/ops/components`. Query: `component`, `project`, `repo`, `depth`, `direction`. Unknown identity 400; not found 404.

## Tests

- Endpoint with `component` round-trips YAML; missing project/repo fails validate.
- Unknown component name fails validate.
- Path-only endpoints still validate.
- `resolve_graph_endpoint_id` returns `component:…`.
- Neighborhood: `web` depth 1 includes `api` via `depends_on`; depth 0 is origin only.
- Declared `graph.relationships` with `from.component` / `to.component` appears as `origin: declared`.
- Path-based declared edge resolves through `ComponentResolver`.
- Cross-repo `ComponentRef` is included.
- No-components catalog: graph of a missing name is not-found, not a crash.

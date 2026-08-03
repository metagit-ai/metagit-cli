# RFC-0018: Pluggable Ontology Layer — Design

**Status:** Proposed  
**Date:** 2026-07-31  
**Series:** [Central State Plane series index](2026-07-31-central-state-plane-series-index.md)  
**Depends on:** RFC-0015 DocumentStore namespaces; optionally RFC-0016 catalog refs; RFC-0014 Atlas, RFC-0010 semantic KG, GitNexus as **adapters**  
**Plan:** (pending)

## Summary

Add a **pluggable ontology / knowledge adapter layer** so agents can ask for small, typed knowledge slices (“who owns auth?”, “what capabilities touch billing?”) without Metagit owning a single universal ontology database. Adapters project Atlas, semantic ownership, GitNexus, or external graphs into a common **KnowledgeSlice** DTO sized for prompts. Optional plane persistence caches slices and org-level overlays under `ontology.*`.

## Goals

1. Define `OntologyAdapter` Protocol: `id`, `describe`, `query`, `slice` (budgeted).
2. Ship built-in adapters (read-only wrappers): `semantic` (RFC-0010), `atlas` (RFC-0014 local), `gitnexus` (optional CLI present), `null` (tests).
3. Define `KnowledgeSlice`: concept/capability hits, evidence pointers, owners, confidence, `token_estimate`.
4. CLI + MCP: `metagit ontology query|slice|adapters` with `--max-tokens` and `--adapter`.
5. Optional plane cache: `ontology.cache/{hash}` and org overlay docs `ontology.overlay/document` (CAS).
6. Integrate with RFC-0017 via `knowledge_refs[]` on workload envelopes.
7. Skills-accessible: extend context-pack / harness skills; bundled `metagit-ontology` skill.

## Non-Goals

- Replacing Atlas, GitNexus, or RFC-0010 with one mega-graph.
- Inferring a complete enterprise ontology automatically.
- Requiring any adapter for core Metagit install (all optional).
- Write-back to GitNexus/Atlas from ontology CLI in v1 (reads + optional overlay only).
- Full-text code search (use `workspace grep` / search).

## Decisions (locked)

| # | Decision |
|---|----------|
| D1 | Metagit owns the **adapter interface and slice DTO**, not the ontology content. |
| D2 | Default query path is **fan-out to enabled adapters** with merge + dedupe by `(adapter, entity_id)`. |
| D3 | Token budget is mandatory on `slice`; hard truncate with `truncated=true` flag in result. |
| D4 | Plane storage is optional cache/overlay — adapters remain source of truth for live queries. |
| D5 | No new graph DB dependency; adapters shell out or call in-process services already present. |
| D6 | Classification / least-disclosure: slices honor Atlas access classification when present; never include secrets. |

## Architecture

```text
metagit ontology query|slice
        │
        ▼
 OntologyService
   ├─► AdapterRegistry (semantic, atlas, gitnexus, …)
   ├─► Merge / budget trim → KnowledgeSlice
   └─► optional DocumentStore ontology.cache / ontology.overlay  (0015)
```

### Protocols

```python
class OntologyAdapter(Protocol):
  id: str
  def describe(self) -> dict[str, Any]: ...
  def query(
    self,
    text: str,
    *,
    project: str | None,
    repo: str | None,
    limit: int,
  ) -> list[KnowledgeHit]: ...
  def slice(
    self,
    hit_ids: list[str],
    *,
    max_tokens: int,
  ) -> KnowledgeSlice: ...
```

### Models (proposed)

- `KnowledgeHit`: `adapter`, `entity_id`, `kind` (concept|capability|symbol|owner|…), `title`, `score`, `project?`, `repo?`
- `KnowledgeSlice`: `hits`, `evidence[]` (path/symbol/uri), `owners[]`, `notes[]`, `token_estimate`, `truncated`, `adapter_errors[]`
- `OntologyOverlay` (optional plane doc): org aliases / banned concepts / prefer-adapter rules — small YAML/JSON, CAS-backed

## Interfaces

### CLI

```bash
metagit ontology adapters --json
metagit ontology query "authentication" [--project P] [--repo R] [--adapter semantic] [--json]
metagit ontology slice --from-query "…" --max-tokens 800 [--json]
```

### MCP

`metagit_ontology_adapters`, `metagit_ontology_query`, `metagit_ontology_slice`

### Config

```yaml
config:
  ontology:
    enabled_adapters: [semantic, atlas]  # gitnexus opt-in
    default_max_tokens: 800
    cache: false                         # plane cache
```

### Plane namespaces

| Namespace | Purpose |
|-----------|---------|
| `ontology.cache` | Optional query/slice cache keys |
| `ontology.overlay` | Org overlay document |

### Skills

- `metagit-ontology`: when to query vs grep vs Atlas CLI; always pass `--max-tokens`; prefer slice after harness `next`.
- Cross-link from `metagit-context-pack`, `metagit-workload-harness`, `metagit-repo-impact`.

## Relationship to existing systems

| System | Role in 0018 |
|--------|----------------|
| RFC-0010 semantic | Adapter for concept → path ownership |
| RFC-0014 Atlas | Adapter for repo-local capabilities/evidence |
| GitNexus | Optional structural adapter (`query` / impact summaries truncated) |
| RFC-0015 plane | Cache + overlay only |
| RFC-0016 catalog | May store `ontology_refs` on projects later (optional) |
| RFC-0017 harness | `knowledge_refs` → ontology slice |

## Acceptance

- With only `semantic` enabled, query returns hits from `.metagit/graph` concepts without Atlas/GitNexus installed.
- `slice --max-tokens 200` never exceeds budget (token_estimate ≤ max or truncated=true with trimmed body).
- Adapter failure is soft: listed in `adapter_errors`, other adapters still return.
- MCP tools return JSON DTOs suitable for agent consumption.
- Docs clarify Metagit is not the ontology authority.

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| 0015 namespaces; 0010/0014/GitNexus as adapters | 0017 knowledge_refs; lean agent prompts |

## Open questions

1. Should overlay editing be CLI-only or also web Config Studio?  
   **Recommendation:** CLI/MCP first; web later.
2. One merged slice vs per-adapter slices in MCP response?  
   **Recommendation:** one merged slice + `by_adapter` optional map behind `--verbose`.

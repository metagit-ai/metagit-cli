# RFC-0010: Semantic Repository Knowledge Graph — Design

**Status:** Draft  
**Date:** 2026-07-09  
**Series:** [ACL RFC series index](2026-07-09-acl-rfc-series-index.md)  
**Vision:** [agent-coordination.md](../../reference/agent-coordination.md) (RFC-0007 vision; original spec.md retired) § Semantic Ownership  
**Depends on:** RFC-0007 claims; RFC-0008 models helpful for scoping  
**Plan:** [2026-07-09-rfc-0010-semantic-kg.md](../plans/2026-07-09-rfc-0010-semantic-kg.md)

## Summary

Add **concept-level ownership** (Authentication, Billing, …) mapped to paths/symbols so agents can detect likely conflicts before editing. Persist a lightweight workspace graph under `.metagit/graph/`. Integrate with advisory claims; optionally consume GitNexus/detect signals without replacing those systems.

## Goals

- Models: `Concept`, `ConceptOwnership` (concept → path globs / repo), optional symbol hints.
- Ingest: deterministic from detect/index metadata + manual declare; optional GitNexus overlay import.
- CLI/MCP: query concepts, suggest owners for a path, check concept conflict vs active claims/agents.
- Feed claim advice: `claim check` / declare may warn on concept overlap (still advisory).

## Non-Goals

- Replacing GitNexus or becoming a general code-intel product.
- Org-wide hosted KG SaaS.
- Enforcing hard locks on concepts.
- Merge/scheduler/AOS engines.

## Architecture

```text
detect / index / optional GitNexus
        │
        ▼
 SemanticGraphService  ──►  .metagit/graph/
        │
        ├── Concept nodes
        ├── path/symbol edges
        └── conflict hints ──► ClaimService (advisory)
```

**Package:** `src/metagit/core/semantic/`

## Interfaces

### CLI

```bash
metagit semantic ingest [--project P] [--json]
metagit semantic declare --concept Authentication --repository P/R --pattern '**/auth/**'
metagit semantic query --concept Authentication [--json]
metagit semantic owners --path backend/auth/token.py --repository P/R [--json]
metagit semantic conflicts --repository P/R [--json]
```

### MCP

`metagit_semantic_ingest`, `metagit_semantic_query`, `metagit_semantic_owners`, `metagit_semantic_conflicts`

## Persistence

```text
.metagit/graph/
  concepts.json
  ownerships.json
  events/semantic.jsonl   # optional
```

## Events

`ConceptDeclared`, `ConceptConflictHint` with `source=semantic`.

## Acceptance

- Declare concept + path; `owners` returns it for matching files.
- Overlapping active claims on same concept produce conflict hint JSON.
- Does not block git; tests cover overlap logic; docs + modality features.

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| ACL claims, detect/index; 0008 optional | 0009 path hints, 0011 conflict context, 0013 |

## Open questions

1. Bootstrap concept catalog from a bundled ontology vs empty-by-default?
2. How deep should GitNexus import go in v1?

**Recommendation:** empty-by-default + small bundled seed optional flag; GitNexus import as optional phase, not MVP.

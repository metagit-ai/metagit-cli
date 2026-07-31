# Central State Plane Series Index (RFC-0015–0018)

**Status:** Living index  
**Date:** 2026-07-31  
**Vision:** Metagit as an org control plane — shared central state for project footprint, multi-repo agent coordination, lean agent harnessing, and pluggable knowledge — without requiring a git repository as the sole core of truth.

## Why this series exists

Today Metagit has two persistence layers:

1. **Catalog / footprint** — git-tracked `.metagit.yml` (projects, repos, graph).
2. **Coordination state** — local `.metagit/` JSON, optionally shared via HTTP (`RemoteHttpBackend` → `metagit web serve`). See [sharing-state.md](../../reference/sharing-state.md) and [remote-state-backend-design](2026-07-01-remote-state-backend-design.md).

ACL, task graph, scheduler, merge, and semantic stores remain **local filesystem** under the session/manifest root. Architecture still states there is no application database backing core runtime flows.

This series evolves that into a **pluggable central state plane** so organizations can run multi-agent, multi-host workloads against DynamoDB, MongoDB, or an ops HTTP front-end, while keeping `local` as the zero-config default for single-machine use.

## Relationship to ACL series (0007–0014)

| Series | Owns |
|--------|------|
| [ACL RFC series 0007–0013](2026-07-09-acl-rfc-series-index.md) + [Atlas 0014](2026-07-14-rfc-0014-atlas-design.md) | Agent coordination engines, composition, repo-local semantics |
| **This series 0015–0018** | Where that state lives at org scale; catalog without git-as-sole-truth; lean harness; ontology adapters |

**Git authority unchanged:** central state never replaces Git as source of truth for *code*. It becomes authoritative for *org footprint metadata and agent coordination documents* when configured.

## Dependency graph

```text
RFC-0015 Central State Plane (foundation)
  ├─► RFC-0016 Org Catalog Backend
  ├─► RFC-0017 Agentic Workload Harness
  │     (uses 0015 namespaces + existing 0008–0013 engines)
  └─► RFC-0018 Pluggable Ontology Layer
        (uses 0015 namespaces; adapters over Atlas / 0010 / GitNexus / external)
```

## Status table

| RFC | Title | Design | Plan | Status |
|-----|-------|--------|------|--------|
| 0015 | Central State Plane | [design](2026-07-31-rfc-0015-central-state-plane-design.md) | (pending) | **Proposed** |
| 0016 | Org Catalog Backend | [design](2026-07-31-rfc-0016-org-catalog-backend-design.md) | (pending) | **Proposed** |
| 0017 | Agentic Workload Harness | [design](2026-07-31-rfc-0017-agentic-workload-harness-design.md) | (pending) | **Proposed** |
| 0018 | Pluggable Ontology Layer | [design](2026-07-31-rfc-0018-pluggable-ontology-layer-design.md) | (pending) | **Proposed** |

## Shared locks (all RFCs in this series)

- **Default backend remains `local`.** No behavior change without explicit config/env.
- **No forced cloud SDKs** in the base `metagit-cli` install. DynamoDB / MongoDB via optional extras.
- **Optimistic concurrency** (`StateToken` + conflict retry) is the universal write model for documents.
- **Git remains authoritative for source code.** Catalog/state plane authority is for metadata and coordination only.
- **Modality default:** CLI + MCP + core services + docs/skills. SPA only where ops HTTP already exists.
- **Secrets never logged**; tokens redacted in appconfig preview.
- **YAGNI on engines:** 0015 does not reimplement task/scheduler/merge/atlas — it provides the store those engines can migrate onto.

## Build order

1. Ship **0015** Phase 0–1 (protocol + adapt coordination docs + one cloud backend).
2. **0016** once DocumentStore namespaces are stable.
3. **0017** once coord + ACL namespaces can host session/task envelopes.
4. **0018** once query/list_prefix and a stable document schema exist for knowledge slices.

## Document conventions

Each **design** includes: Summary, Goals, Non-Goals, Architecture, Interfaces, Persistence, Acceptance, Dependencies, Decisions (locked), Open questions (if any).

Each **plan** (when written) lives under `docs/superpowers/plans/` and follows the writing-plans skill format.

# RFC-0016: Org Catalog Backend — Design

**Status:** Proposed  
**Date:** 2026-07-31  
**Series:** [Central State Plane series index](2026-07-31-central-state-plane-series-index.md)  
**Depends on:** RFC-0015 Central State Plane (DocumentStore + namespaces)  
**Related:** Workspace catalog (`WorkspaceCatalogService`), `.metagit.yml`, provider source sync  
**Plan:** (pending — after 0015 ships or in parallel once 0015 Phase 0–1 APIs freeze)

## Summary

Make the **organizational project footprint** (projects, repos, tags, documentation links, graph relationships) available from the central state plane so Metagit does not require a git-tracked coordinator repository as the only source of truth. `.metagit.yml` remains a first-class **export/import and local cache** format; when `catalog` backend is enabled, the plane document is authoritative for catalog reads/writes across agents and hosts.

## Goals

1. Persist a versioned **workspace catalog document** under namespace `catalog.workspace` (and optional per-project keys).
2. Keep full Pydantic validation parity with today’s `MetagitConfig` / workspace models — no parallel schema dialect.
3. Support modes: `manifest` (today), `plane` (plane authoritative), `mirror` (plane + write-through export to `.metagit.yml`).
4. Provide CLI/MCP for pull/push/diff between local manifest and plane.
5. Preserve protected-project and force-flag semantics on mutations.
6. Allow agents to bootstrap context packs / search **without** cloning a metagit coordinator repo (they still clone *managed* code repos as today).

## Non-Goals

- Replacing Git remotes or provider APIs for code.
- Auto-discovering every org repo without existing source-sync flows (reuse `project source sync`).
- Ontology / knowledge graphs (RFC-0018).
- Rewriting WorkspaceCatalogService from scratch — prefer a `CatalogStore` port behind it.
- Multi-document CRDTs; CAS on the catalog document(s) is enough for v1.

## Decisions (locked)

| # | Decision |
|---|----------|
| D1 | Catalog body is the existing workspace subset of `.metagit.yml` (or full `MetagitConfig` envelope) serialized as JSON in the plane; YAML file remains the human/git format. |
| D2 | Default mode stays `manifest` forever unless configured. |
| D3 | `mirror` is the recommended team mode: plane is shared truth; local `.metagit.yml` is a checkout cache for humans/CI that prefer files. |
| D4 | Graph relationships live in the same catalog document as today (no separate graph store in 0016). |
| D5 | Mutations go through existing catalog services so MCP/HTTP v2 stay consistent. |

## Architecture

```text
WorkspaceCatalogService / ConfigManager
        │
        ▼
 CatalogStore Protocol
   load() / save(expected) / diff()
        │
   ┌────┴─────┐
   ▼          ▼
 Manifest   Plane DocumentStore
 (.yml)     (catalog.workspace / key=document)
```

### Modes

| Mode | Read | Write |
|------|------|-------|
| `manifest` | `.metagit.yml` | `.metagit.yml` |
| `plane` | DocumentStore | DocumentStore |
| `mirror` | Plane (fallback manifest if empty) | Plane + export YAML |

### Namespace keys

| Ref | Body |
|-----|------|
| `catalog.workspace` / `document` | Full workspace catalog envelope (projects[], graph, metadata) |
| `catalog.workspace` / `revision_meta` (optional) | `{updated_by, updated_at, note}` for doctor/diff UX |

## Interfaces

### Config

```yaml
config:
  catalog:
    mode: manifest   # manifest | plane | mirror
    # reuses config.state org_id / workspace_id / backend
```

Env: `METAGIT_CATALOG_MODE`.

### CLI (proposed)

```bash
metagit catalog status --json
metagit catalog pull [--force]      # plane → local yml
metagit catalog push [--force]      # local yml → plane (CAS)
metagit catalog diff --json
```

Existing `metagit workspace list|add|…` honor `catalog.mode`.

### MCP

`metagit_catalog_status`, `metagit_catalog_pull`, `metagit_catalog_push`, `metagit_catalog_diff` — plus existing workspace catalog tools reading through `CatalogStore`.

### Skills

- Extend `metagit-workspace-scope` and `metagit-sharing-state` with catalog mode.
- Optional bundled skill `metagit-org-catalog` when implementation lands.

## Persistence

- Plane: RFC-0015 `DocumentStore` CAS on `catalog.workspace`/`document`.
- Manifest: existing YAML load/save/validate path.
- Conflict: push/pull with stale token fails clearly; `--force` only for pull overwrite of local file after confirmation / agent_mode rules.

## Acceptance

- `mode=manifest` is identical to today’s behavior.
- Two agents on `mode=plane` with shared Dynamo/HTTP see the same `workspace list`.
- `mirror` push then pull on a second host yields schema-valid `.metagit.yml`.
- Protected projects still block mutations without `force`.
- Context pack tier 0 works with plane-backed catalog (no coordinator git clone required for *catalog*, only for code repos as configured).

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| RFC-0015 DocumentStore | RFC-0017 harness (workspace map from plane) |
| WorkspaceCatalogService, MetagitConfig models | RFC-0018 (attach ontology refs to projects/repos) |

## Open questions

1. Full `MetagitConfig` in plane vs workspace-only subset?  
   **Recommendation:** workspace + graph + top-level name/description; omit detection noise fields until needed.
2. Should `project source sync --write` update plane directly in `plane`/`mirror` modes?  
   **Recommendation:** yes — through CatalogStore only.

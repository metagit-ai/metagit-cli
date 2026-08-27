# RFC-0023: Workspace Federation & Org-Scale Identity — Design

**Status:** Proposed  
**Date:** 2026-08-27  
**Series:** [Agent Reliability series index](2026-08-27-agent-reliability-series-index.md)  
**Depends on:** RFC-0015 (DocumentStore / plane partitions), RFC-0016 (org catalog backend), shipped `config.state.org_id` / `workspace_id`, context packs, `WorkspaceCatalogService`  
**Plan:** (pending — `docs/superpowers/plans/2026-08-27-rfc-0023-federation.md`)  
**Related:** [RFC-0016 org catalog](2026-07-31-rfc-0016-org-catalog-backend-design.md) · [Central state plane index](2026-07-31-central-state-plane-series-index.md) · skill `metagit-sharing-state`

## Summary

Multi-workspace operators need **stable org + workspace identity**, a **read-only federated view** of linked workspaces, and CLI discovery without cloning every coordinator repo. **RFC-0023 formalizes identity fields**, adds **`metagit workspace link`** to register remote workspace descriptors, and **`metagit federation status`** for health/readiness across links. v1 targets **dozens of workspaces** (series D5); hundreds defer to RFC-0016 catalog backend maturity + RFC-0025 indexing. Federation is **read-mostly** — mutations stay on the home workspace unless explicitly routed through plane catalog push (RFC-0016).

## Goals

1. **Identity model** — canonical `org_id`, `workspace_id`, `workspace_slug`, optional `display_name` on manifest and appconfig; env overrides documented (`METAGIT_STATE_ORG_ID`, `METAGIT_STATE_WORKSPACE_ID`).
2. **Federation registry** — local file `.metagit/federation/links.yaml` listing linked workspace descriptors (plane endpoint, manifest URL, or local path).
3. **`metagit workspace link add|remove|list`** — manage links; validate reachability; store last-seen catalog hash.
4. **`metagit federation status --json`** — rollup: linked workspace count, reachable count, aggregate repo/project counts, per-link blockers.
5. **Federated read-only catalog** — `metagit federation catalog [--workspace WS] --json` merges tier-0 map rows from linked workspaces without mutating local manifest.
6. **Context pack extension (optional v1.1)** — `metagit context pack --tier 0 --include-federated` adds linked workspace maps with clear `source_workspace_id` attribution.
7. **Coordinate with RFC-0016** — when `catalog.mode=plane`, link descriptors reference plane `org_id`/`workspace_id` partitions; manifest links remain fallback.
8. **Parity** — MCP tools, skill `metagit-sharing-state`, docs `docs/reference/federation.md`, modality registry.

## Non-Goals

- Cross-workspace ACL lease sharing or global branch allocation (each workspace remains sovereign).
- Bi-directional manifest sync / CRDT merge across workspaces in v1.
- Org-wide RBAC or SSO integration.
- Replacing RFC-0016 — federation **consumes** catalog documents; 0016 **stores** authoritative catalog when plane enabled.
- Auto-cloning all repos from linked workspaces.
- Hundreds-of-workspaces search performance (RFC-0025 + RFC-0016 scale work).

## Decisions (locked)

| # | Decision |
|---|----------|
| D1 | Scale target: **≤ ~50 linked workspaces** per operator machine in v1; status command completes ≤ 5s with cached descriptors. |
| D2 | Federation links are **local operator config** under `.metagit/federation/` — not committed to git by default (`.gitignore` template documents opt-in). |
| D3 | **Read-only by default** — no command mutates a remote workspace; `catalog pull` from link requires explicit `--apply-local` (out of scope v1). |
| D4 | Identity fields reuse **`config.state.org_id` / `workspace_id`** — no parallel id scheme. |
| D5 | Link descriptor MUST include **`workspace_id` + one resolution strategy** (local path, manifest URL, or plane ref). |
| D6 | Unreachable links degrade gracefully — status reports `reachable: false`, federation catalog skips with warning in JSON. |
| D7 | Dedupe project/repo names across federation by **`(source_workspace_id, project, repo)` tuple** — collisions surfaced, not silently merged. |
| D8 | Federation does not bypass workspace **gate** — inactive home workspace still blocks mutating commands locally. |

## Architecture

```text
Home workspace (.metagit.yml + config.state)
        │
        ▼
 FederationRegistry (.metagit/federation/links.yaml)
        │
        ▼
 FederationService
   ├─► LinkResolver (local path | HTTP manifest | plane DocumentStore)
   ├─► FederatedCatalogReader (read-only MetagitConfig slice)
   └─► FederationStatusAggregator
        │
        ▼
 CLI / MCP / context pack (optional federated tier-0)
```

**Coordinate with RFC-0016:**

```text
RFC-0016 CatalogStore (plane/manifest/mirror)
        ▲
        │ authoritative write path
        │
Home workspace catalog ◄──── FederationService (read-only pull per link)
        │
Linked workspace A catalog (plane or manifest)
Linked workspace B catalog (…)
```

**Package placement (proposed):**

| Module | Role |
|--------|------|
| `src/metagit/core/federation/models.py` | `WorkspaceIdentity`, `FederationLink`, `FederationStatus`, `FederatedRepoRow` |
| `src/metagit/core/federation/registry.py` | Load/save links.yaml |
| `src/metagit/core/federation/resolver.py` | Resolve link → catalog document |
| `src/metagit/core/federation/service.py` | status, catalog merge, link CRUD |
| `src/metagit/cli/commands/federation.py` | `federation status`, `federation catalog` |
| `src/metagit/cli/commands/workspace.py` | extend with `workspace link` subcommands |

## Identity model

### Manifest / appconfig

```yaml
config:
  state:
    org_id: acme-corp
    workspace_id: platform-eng
  federation:
    slug: platform-eng           # human-friendly short name
    display_name: Platform Engineering
```

Env overrides (existing): `METAGIT_STATE_ORG_ID`, `METAGIT_STATE_WORKSPACE_ID`.

### WorkspaceIdentity DTO

```python
class WorkspaceIdentity(BaseModel):
    org_id: str
    workspace_id: str
    slug: str | None = None
    display_name: str | None = None
    home_root: str              # absolute path to manifest root
    catalog_mode: Literal["manifest", "plane", "mirror"] = "manifest"
```

Doctor/summary (RFC-0020) may surface missing identity as readiness warning when federation links exist.

## Link descriptor

`.metagit/federation/links.yaml`:

```yaml
links:
  - id: data-platform
    workspace_id: data-platform
    org_id: acme-corp
    display_name: Data Platform
    resolve:
      kind: plane              # plane | manifest_url | local_path
      plane:
        backend: http          # reuses config.state.backend profile name or inline
        base_url: https://plane.example/api
      # manifest_url: https://git.example/platform/.metagit.yml
      # local_path: ../other-workspace
    last_seen_at: null
    last_catalog_hash: null
```

**Resolve kinds:**

| Kind | Use case |
|------|----------|
| `local_path` | Monorepo checkout or sibling directory on same machine |
| `manifest_url` | Raw HTTPS fetch of `.metagit.yml` (read-only) |
| `plane` | RFC-0015 DocumentStore read of `catalog.workspace` document |

## Interfaces

### CLI

```bash
# Link management (under workspace group)
metagit workspace link list [--json]
metagit workspace link add --id ID --workspace-id WS [--org-id ORG] \
  (--local-path PATH | --manifest-url URL | --plane-backend PROFILE)
metagit workspace link remove ID
metagit workspace link probe ID [--json]   # reachability check

# Federation rollup
metagit federation status [--json]
metagit federation catalog [--workspace ID] [--json]
metagit federation identity show [--json]    # home workspace identity
```

### MCP (ACTIVE-gated)

| Tool | Purpose |
|------|---------|
| `metagit_federation_status` | Same as CLI status |
| `metagit_federation_catalog` | Federated tier-0 rows |
| `metagit_workspace_link_list` | Link registry |
| `metagit_workspace_link_probe` | Reachability |

### JSON: `federation status`

```json
{
  "generated_at": "2026-08-27T20:00:00Z",
  "home": {
    "org_id": "acme-corp",
    "workspace_id": "platform-eng",
    "slug": "platform-eng",
    "projects": 3,
    "repos": 12
  },
  "links": [
    {
      "id": "data-platform",
      "workspace_id": "data-platform",
      "reachable": true,
      "projects": 2,
      "repos": 8,
      "last_seen_at": "2026-08-27T19:55:00Z",
      "blockers": []
    }
  ],
  "aggregate": {
    "linked_workspaces": 1,
    "reachable": 1,
    "total_repos": 20,
    "duplicate_repo_names": []
  }
}
```

### Federated catalog rows

Each repo row extends tier-0 map entry with:

- `source_workspace_id`
- `source_link_id`
- `federated: true`

No write API in v1.

## Persistence

| Artifact | Path | Git? |
|----------|------|------|
| Home identity | `.metagit.yml` / appconfig | yes |
| Federation links | `.metagit/federation/links.yaml` | default no (document opt-in) |
| Cached remote catalog snapshot | `.metagit/federation/cache/{link_id}.json` | no |
| Plane catalog | RFC-0016 namespace | when plane mode |

Cache TTL default 15m; `--refresh` bypasses cache on status/catalog.

## Acceptance

- Home workspace with `org_id` + `workspace_id` returns them via `federation identity show --json`.
- `workspace link add --local-path ../fixture` + `federation status` reports reachable link with repo counts.
- Unreachable link (bad URL) → `reachable: false`, non-zero exit only when `--require-all` flag set.
- `federation catalog --json` returns repos from home + linked workspaces with `source_workspace_id` on federated rows.
- Duplicate `(project, repo)` simple names across links appear in `duplicate_repo_names[]` without silent overwrite.
- Plane-backed link (RFC-0016 fixture) resolves catalog document read-only.
- MCP parity for status + catalog.
- Works at **50-link fixture** within 5s using cache (benchmark test, not CI default).
- Modality entries `federation_status`, `workspace_link`; skill `metagit-sharing-state` updated.
- RFC-0016 index cross-link notes federation read path; no public RFC stub until shipped.

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| RFC-0015 plane partitions | Plane link resolution |
| RFC-0016 catalog document | Authoritative remote catalog reads |
| RFC-0020 discovery/summary | Identity readiness signals |
| RFC-0025 indexing (later) | Federated grep at scale |
| RFC-0022 policy (later) | Cross-workspace mutation remains local-only |

## Suggested PR split

1. **Identity** — models, `federation identity show`, manifest validation, doctor warning.
2. **Link registry** — add/remove/list/probe, local_path resolver, cache.
3. **Federation status + catalog** — merge tier-0, CLI/MCP.
4. **Plane + manifest_url resolvers** — RFC-0016 integration tests.
5. **Docs + skill** — federation.md, sharing-state skill, examples snippet.

## Open questions

1. Commit `.metagit/federation/links.yaml` to team repos?  
   **Recommendation:** default gitignore; document `--track-links` init flag for teams wanting shared link sets.
2. Should `context pack --tier 0` include federation by default?  
   **Recommendation:** opt-in `--include-federated` — token budget discipline.
3. Namespace for plane federation cache keys?  
   **Recommendation:** local filesystem only in v1; plane `federation.cache` deferred.

# External Repository Nodes & GitHub Organization Index

**Status:** Implemented (initial)  
**Date:** 2026-09-16  
**Principle:** Git stores durable knowledge. The local index stores observations.

## Existing modules to change

| Module | Assumption that changes |
|--------|-------------------------|
| `metagit.core.config.graph_validation` | Endpoints must be workspace `projects[].repos`. **New invariant:** endpoints must resolve to a known repository node (local, curated `graph.nodes`, or org index). |
| `metagit.core.config.graph_resolver` | Maps endpoints only through workspace index rows. Prefer canonical identity when a GitHub URL or org-index hit exists. |
| `metagit.core.config.graph_models` | Single provenance `manual\|promoted\|imported`; no curated external nodes. Add `inferred`/`github` provenance and optional `graph.nodes`. |
| `metagit.core.web.graph_service` | Drops edges whose endpoints are not local index rows. Include external nodes and lifecycle (`known`/`indexed`/`materialized`). |
| `metagit.core.config.graph_cypher_export` | Same local-only skip. Emit canonical ids for GitHub-origin nodes without fake filesystem paths. |
| CLI `main.py`, MCP `tool_registry`/`runtime`, modality registry | No org-index / materialize / graph-neighbors surface. |

Do **not** reuse `project source sync` for this: that flow writes discovered repos into Git-managed `.metagit.yml`. Organization observations stay in SQLite.

## New abstractions

- **`RepositoryIdentity`** (`github://{org}/{repo}`) — stable across known → indexed → materialized. Local path is never the primary key.
- **`RepositoryNode`** — identity, lifecycle (`active`/`archived`/`deleted`/`unknown`), presence (`known`/`indexed`/`materialized`), provenance list (`github`, `local`, `imported`, `inferred`, `manual`).
- **`RepositoryResolver`** — local workspace → curated `graph.nodes` → org index. Used by validation, neighbors, materialize, and graph views.
- **`OrgIndexStore`** — SQLite at `~/.metagit/indexes/github/{org}.sqlite` (`METAGIT_INDEX_HOME` override). Disposable; delete and rebuild from GitHub.
- **`GitHubOrgIndexer`** — list org repos (no clone). Default = metadata; `--refresh` skips unchanged fingerprints; `--full` fetches languages/trees.
- **`OrgSearchService`** / **`RepoMaterializeService`** / **`GraphNeighborhoodService`**.

Fingerprint path markers live in `metagit.core.detect.fingerprints` so GitHub tree indexing shares detector vocabulary (docker, terraform, python, …) without duplicating detector classes.

## CLI (existing conventions)

```text
metagit org index github <organization> [--refresh|--full] [--json]
metagit org search [QUERY] [--language] [--topic] [--has] [--stale-days] [--json]
metagit graph neighbors <repository> [--json]
metagit repo materialize <repository> [--project] [--dry-run] [--json]
```

## Backwards compatibility

Workspaces that never indexed an organization validate and render exactly as today. `config validate` still fails unknown endpoints. Curated `graph.nodes` keep CI green without a local SQLite file.

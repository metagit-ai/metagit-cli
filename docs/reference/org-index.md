# Organization index and external repository nodes

<!-- modality:org_index -->

Git stores durable knowledge. The local index stores GitHub observations.

Use this when an organization is too large to clone, but the metagit graph still needs to talk about those repositories.

## Index a GitHub organization

```bash
metagit org index github my-company
metagit org index github my-company --refresh
metagit org index github my-company --full --json
```

Repositories are enumerated through the GitHub API. Nothing is cloned. The disposable SQLite index lives at `~/.metagit/indexes/github/<org>.sqlite` (override with `METAGIT_INDEX_HOME`). Delete it and re-run the command to rebuild.

Default indexing stores list metadata (identity, description, language, topics, timestamps, visibility, archived). `--refresh` re-fingerprints repositories whose `pushed_at` changed. `--full` also fetches language stats, git tree paths, open PR counts, and the latest release.

Archived GitHub repositories stay in the index. Repositories that disappear from the API are marked `deleted` rather than erased, so historical relationships remain resolvable.

## Search without checkouts

```bash
metagit org search "terraform aws"
metagit org search --language csharp --has azure-pipelines.yml
metagit org search --topic payments --stale-days 730
```

`--has` matches fingerprint paths or detector tags (`docker`, `terraform`, `dotnet`, …). Path markers are shared with local detectors in `metagit.core.detect.fingerprints`.

## Graph neighbors

```bash
metagit graph neighbors payments-api
```

Neighbors can be `materialized`, `indexed`, or `known`. Curated `graph.relationships` in `.metagit.yml` stay in Git. Inferred `similar_to` edges (shared topics) stay in the SQLite index with `provenance: inferred`.

A relationship is valid when both endpoints resolve to a known repository node: a local workspace repo, a curated `graph.nodes[]` entry, or an indexed external repo. Unknown names still fail `metagit config validate`.

Optional curated nodes:

```yaml
graph:
  nodes:
    - identity: github://example-org/shared-auth
      name: shared-auth
      classification:
        domain: identity
        lifecycle: strategic
  relationships:
    - id: payments-auth
      from: { repo: payments-api }
      to: { repo: shared-auth }
      type: depends_on
      provenance: imported
```

Canonical identity is `github://org/repo`. Materializing a repo does not change that identity.

## Materialize one repository

```bash
metagit repo materialize shared-auth
metagit repo materialize shared-auth --project platform --dry-run
```

This clones with existing git machinery, enrolls the repo in `workspace.projects[].repos`, and keeps `github://org/repo` as the graph id.

## MCP and web

ACTIVE-gate MCP tools: `metagit_org_index`, `metagit_org_search`, `metagit_org_repo_get`, `metagit_org_repo_materialize` (`confirm: true` required unless `dry_run`), `metagit_graph_neighbors`.

Web: `GET /v3/ops/org/search` and the existing graph view, which now labels indexed/known nodes.

Existing local-only workspaces are unchanged until an organization is indexed or `graph.nodes` is used.

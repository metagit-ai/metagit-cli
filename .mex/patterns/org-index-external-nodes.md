---
name: org-index-external-nodes
description: Index GitHub organizations into a disposable SQLite store and resolve graph endpoints that are not locally materialized.
triggers:
  - "org index"
  - "external repository"
  - "github://org/repo"
  - "repo materialize"
edges:
  - target: "../context/architecture.md"
    condition: when extending graph validation or MCP tools
  - target: "graph-suggest-maintain.md"
    condition: when changing graph.relationships provenance or validation
  - target: "add-cli-command.md"
    condition: when adding org/graph/repo CLI groups
  - target: "add-mcp-tool.md"
    condition: when adding metagit_org_* tools
last_updated: 2026-09-16
---

# Organization index and external repository nodes

## Context
Load `docs/reference/org-index.md` and `docs/superpowers/specs/2026-09-16-external-repo-org-index-design.md`.
Git stores curated `graph.relationships` / `graph.nodes`. GitHub observations live in `~/.metagit/indexes/github/*.sqlite`.

## Steps
1. Keep canonical identity as `github://org/repo` (`metagit.core.repo.identity`). Do not key graph nodes on local paths.
2. Resolve endpoints with `RepositoryResolver` (local → curated `graph.nodes` → org index). `validate_graph_relationships()` uses that resolver.
3. Index via `GitHubOrgIndexer` + `OrgIndexStore`. Tests inject a fake GitHub client; never clone in the indexer.
4. Fingerprints must use `metagit.core.detect.fingerprints`, not a GitHub-only duplicate of detector logic.
5. Inferred edges stay in SQLite with `provenance: inferred`. Do not write them into Git.
6. `metagit repo materialize` enrolls a catalog URL entry and clones with GitPython. Identity must not change.

## Gotchas
- `project source sync` writes Git-managed `.metagit.yml` and is the wrong tool for a 700-repo observation index.
- Unknown workspace **projects** still fail validation; unknown **repos** may resolve from the index.
- Corrupt SQLite files are renamed `*.sqlite.corrupt` and rebuilt.
- MCP `metagit_org_repo_materialize` requires `confirm: true` unless `dry_run`.
- `METAGIT_INDEX_HOME` overrides `~/.metagit/indexes` for tests.

## Verify
- [ ] `tests/core/orgindex`, `tests/core/repo`, `tests/core/config/test_graph_validation_external.py`
- [ ] CLI tests in `tests/cli/commands/test_org.py`
- [ ] MCP tools listed and `metagit_org_search` callable
- [ ] Local-only graph validation tests still pass

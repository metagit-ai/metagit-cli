# RFC-0025: Workspace Index & Grep Scaling — Design

**Status:** Proposed  
**Date:** 2026-08-27  
**Series:** [Agent Reliability series index](2026-08-27-agent-reliability-series-index.md)  
**Depends on:** Shipped `WorkspaceSearchService` (ripgrep + python_walk fallback), `WorkspaceIndexService`, `metagit workspace grep`, RFC-0023 federation (optional federated scope)  
**Plan:** (pending — `docs/superpowers/plans/2026-08-27-rfc-0025-workspace-index.md`)  
**Related:** [MCP Phase 3 workspace intelligence](2026-05-15-mcp-phase3-workspace-intelligence-design.md) · `.mex/patterns/workspace-content-grep.md`

## Summary

Cross-repo `metagit workspace grep` today fans out ripgrep (or a bounded Python walk) per repository with no persistent workspace-level index. That works for small workspaces but degrades linearly as repo count grows. **RFC-0025 adds an optional on-disk workspace index** under `.metagit/index/` that caches file paths, lightweight metadata, and last-indexed git HEAD — **ripgrep remains the grep backend** for content search. Index build/refresh is explicit or scheduled; **corrupt or stale indexes are ignored safely** with fallback to current behavior.

## Goals

1. **Optional persistent index** — `.metagit/index/manifest.json` + sharded path lists per repo under `.metagit/index/repos/{project}/{repo}.jsonl`.
2. **`metagit workspace index build|status|validate|prune`** — build/refresh, report coverage, validate integrity, drop stale shards.
3. **Grep acceleration** — when index fresh, restrict ripgrep `--files` set or skip missing repos early; **never change hit semantics** vs unindexed grep.
4. **Benchmarks** — fixtures simulating **50** and **200** repos (synthetic tree, CI-friendly) with documented baseline vs indexed latency targets.
5. **Safe degradation** — corrupt JSON, checksum mismatch, or missing shard → log warning, fall back to live filesystem scan for that repo.
6. **Federation-aware scope (v1.1)** — index home workspace only; federated repos excluded until RFC-0023 link cache defines stable roots.
7. **Parity** — MCP `metagit_workspace_index_status`, docs `docs/reference/workspace-index.md`, modality registry.

## Non-Goals

- Replacing ripgrep with an embedded full-text search engine (Elasticsearch, tantivy, etc.).
- Indexing file **contents** in v1 — path/metadata only; content search still delegated to ripgrep.
- Real-time filesystem watchers / inotify daemon.
- Semantic or symbol indexing (GitNexus / Atlas remain separate).
- Distributed index sharding across hosts (local index only).
- Mandatory index — workspaces without index behave exactly as today.

## Decisions (locked)

| # | Decision |
|---|----------|
| D1 | **Ripgrep stays the content grep backend** — index narrows candidate files and repo list only. |
| D2 | Index storage default **`.metagit/index/`** — gitignored like other `.metagit/` runtime state unless team opts in. |
| D3 | **Corrupt index ignored** — per-repo shard failure must not fail grep command. |
| D4 | Freshness keyed on **`(repo_path, head_commit, manifest_repo_hash)`** — any mismatch triggers shard stale status. |
| D5 | Index build is **explicit or `--if-stale`** — no automatic full rebuild on every grep in v1. |
| D6 | Python walk fallback when ripgrep missing **does not use index** in v1 (path list still helps ripgrep-only fast path). |
| D7 | Benchmark targets are **informational** — not hard CI gates until fixtures stable; publish numbers in docs. |
| D8 | Max shard size soft cap **500k paths/repo** — truncate with `truncated: true` flag in shard metadata. |

## Architecture

```text
metagit workspace grep QUERY
              │
              ▼
     WorkspaceSearchService
              │
      ┌───────┴───────┐
      ▼               ▼
 WorkspaceIndex   ripgrep (per repo)
 Service          (content search)
 (path sets)
      │
      ▼
 .metagit/index/
   manifest.json
   repos/{project}/{repo}.jsonl
```

**Index build pipeline:**

```text
metagit workspace index build [--if-stale] [--json]
              │
              ▼
     WorkspaceIndexBuilder
       ├─► WorkspaceIndexService.build_index()  (repo list)
       ├─► per repo: git ls-files + ignored walk fallback
       ├─► compute head_commit + manifest hash
       └─► atomic write shard (tmp + rename)
```

**Package placement (proposed):**

| Module | Role |
|--------|------|
| `src/metagit/core/workspace/index_models.py` | `IndexManifest`, `RepoIndexShard`, `IndexStatus` |
| `src/metagit/core/workspace/index_builder.py` | Build/prune/validate |
| `src/metagit/core/workspace/index_reader.py` | Safe load + staleness checks |
| `src/metagit/core/mcp/services/workspace_search.py` | Integrate optional path filter |
| `src/metagit/cli/commands/workspace.py` | `workspace index` subcommands |

## Index formats

### `manifest.json`

```json
{
  "version": 1,
  "generated_at": "2026-08-27T21:00:00Z",
  "workspace_root": "/path/to/ws",
  "config_path": "/path/to/ws/.metagit.yml",
  "repos_indexed": 48,
  "repos_stale": 2,
  "repos_failed": 0,
  "shards": [
    {
      "project": "demo",
      "repo": "api",
      "shard_path": "repos/demo/api.jsonl",
      "path_count": 1240,
      "head_commit": "abc123…",
      "manifest_hash": "sha256:…",
      "status": "fresh"
    }
  ]
}
```

### Repo shard (`*.jsonl`)

One JSON object per line:

```json
{"path": "src/main.py", "size": 4021, "mtime": 1690000000}
```

Content hashing omitted in v1 for build speed.

## Interfaces

### CLI

```bash
metagit workspace index build [--if-stale] [--project P] [--repo R] [--json]
metagit workspace index status [--json]
metagit workspace index validate [--json]
metagit workspace index prune [--json]    # remove shards for repos no longer in manifest

# existing grep — gains optional flags
metagit workspace grep "PATTERN" [--use-index | --no-index] …
```

**`workspace index status` JSON:**

```json
{
  "index_present": true,
  "version": 1,
  "generated_at": "2026-08-27T21:00:00Z",
  "coverage_pct": 96.0,
  "repos_total": 50,
  "repos_fresh": 48,
  "repos_stale": 2,
  "repos_missing_shard": 0,
  "grep_backend": "ripgrep",
  "recommendation": "metagit workspace index build --if-stale"
}
```

### MCP (ACTIVE-gated)

| Tool | Purpose |
|------|---------|
| `metagit_workspace_index_status` | Same as CLI status |
| `metagit_workspace_index_build` | Async-friendly build with `if_stale` (confirm flag for full rebuild) |

Existing `metagit_workspace_grep` gains optional `use_index: bool` (default true when index present).

### Grep integration

When index fresh for repo:

1. Load path list from shard.
2. Pass files to ripgrep via `--files` or `-g` patterns (implementation choice — prefer `--files-from` temp file when list &lt; 50k paths).
3. On shard load error → log + fall back to unrestricted repo grep.

Semantical identity requirement: indexed grep MUST return same hits as `--no-index` on clean fixture (integration test).

## Persistence

| Artifact | Path | Notes |
|----------|------|-------|
| Manifest | `.metagit/index/manifest.json` | Checksum optional v1.1 |
| Shards | `.metagit/index/repos/{project}/{repo}.jsonl` | Atomic replace |
| Temp | `.metagit/index/.tmp/` | Build staging |

Corrupt manifest → treat as no index globally (grep uses today's path).

## Benchmarks

Fixtures under `tests/fixtures/workspace_scale/` (generated, not committed full 200-repo trees — generator script in repo):

| Fixture | Repos | Files/repo (avg) | Target build | Target grep (warm) |
|---------|-------|------------------|--------------|---------------------|
| `ws_50` | 50 | 200 | ≤ 30s local | ≤ 2s ripgrep fan-out |
| `ws_200` | 200 | 100 | ≤ 120s local | ≤ 8s ripgrep fan-out |

Benchmark script: `scripts/bench-workspace-index.py` writes JSON results for docs. CI runs **`ws_50` only** on nightly marker.

## Acceptance

- Without index, `workspace grep` behavior unchanged (regression suite green).
- After `index build`, `index status` shows `coverage_pct` and fresh shards.
- Corrupt shard file → grep still succeeds via fallback; validate reports shard error.
- `--no-index` forces legacy path even when index present.
- `index prune` removes shards for deleted manifest repos.
- MCP status/build parity.
- Benchmark docs published with measured speedup on `ws_50` fixture.
- Modality `workspace_index`; reference doc when shipped.
- Federation links do not break index build (home repos only).

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| WorkspaceSearchService | Grep integration point |
| WorkspaceIndexService | Repo enumeration |
| RFC-0023 federation (optional) | Future federated index scope |
| RFC-0020 discovery | May surface index staleness in summary v1.1 |

## Suggested PR split

1. **Index models + builder** — build/status/validate/prune, unit tests with tmp_path.
2. **Grep integration** — `--use-index`, fallback paths, semantic parity test.
3. **Benchmark fixtures + script** — ws_50 generator, nightly job.
4. **MCP + docs** — tools, workspace-index.md, modality parity.

## Open questions

1. Commit index to git for CI caches?  
   **Recommendation:** no — local/ephemeral; CI builds index in job when testing indexed grep.
2. Include **git-ignored files** in index?  
   **Recommendation:** default `git ls-files` only; `--include-untracked` flag on build for special cases.
3. Should `workspace summary` show index staleness?  
   **Recommendation:** v1.1 optional dimension; not in initial readiness score.

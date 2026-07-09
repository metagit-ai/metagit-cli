---
name: merge-orchestrator-store
description: Implementing or extending RFC-0011 merge orchestrator models, paths, JSON store, git ops, service, and events.
triggers:
  - "merge orchestrator"
  - "RFC-0011"
  - "MergeStore"
  - ".metagit/merges"
edges:
  - target: "../context/conventions.md"
    condition: when writing or reviewing merge orchestrator code
  - target: "semantic-graph-service.md"
    condition: when mirroring RFC package, model, and store patterns
last_updated: 2026-07-09
---

# Merge Orchestrator Store

## Context
RFC-0011 merge state lives under `src/metagit/core/merge/`.
The package follows the taskgraph/semantic style: Pydantic models, path helpers,
file-backed JSON stores, advisory locks, `T | Exception` service/store returns,
and JSONL events under `.metagit/events/`.

## Steps
1. Start with focused tests under `tests/core/merge/`.
2. Keep persistence in `MergeStore`; keep local git mutation in `git_ops`; keep
   orchestration and event emission in `MergeOrchestrator`.
3. Validate ids as slugs and repositories as `project/repo` at the model layer.
4. Store merge documents under `.metagit/merges/<merge_id>.json`.
5. Keep `queue.json` as a lightweight index sorted by `merge_id`.
6. Export public model and store types from `metagit.core.merge.__init__`.

## Gotchas
- Do not implement later CLI/MCP/validator layers unless the task explicitly
  opens those layers.
- Missing merge documents should return `FileNotFoundError`; missing queue files
  should return an empty `MergeQueue`.
- Queue upserts should happen after saving a merge request and must be protected
  by the same advisory lock pattern used by taskgraph.
- `events_file()` should point to `.metagit/events/merge.jsonl` even before an
  event writer exists.
- `attempt_merge()` must abort conflicts before returning and must not leave
  `.git/MERGE_HEAD` behind.
- Conflict handling may fill ACL command hint strings, but must not mutate ACL
  branch, lease, worktree, or claim state.

## Verify
- [ ] `uv run pytest tests/core/merge`
- [ ] `uv run ruff check src/metagit/core/merge tests/core/merge`
- [ ] `task qa:prepush`
- [ ] `task gitnexus:analyze`

## Debug
- Import errors usually mean `__init__.py` exports or package files are missing.
- Queue ordering failures usually mean the store upsert did not sort by
  `merge_id`.
- Store validation failures usually mean raw JSON was not validated through
  `MergeRequest` / `MergeQueue`.

## Update Scaffold
- [ ] Update `.mex/ROUTER.md` "Current Project State" when RFC-0011 scope changes.
- [ ] Update any `.mex/context/` files that become stale.
- [ ] Add docs/CLI/MCP modality entries only when those surfaces are exposed.

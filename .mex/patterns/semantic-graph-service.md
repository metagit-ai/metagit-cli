---
name: semantic-graph-service
description: Implementing or extending RFC-0010 semantic graph models, JSON store, service queries, and events.
triggers:
  - "semantic graph"
  - "RFC-0010"
  - "concept ownership"
  - "SemanticGraphService"
edges:
  - target: "../context/conventions.md"
    condition: when writing or reviewing semantic graph code
  - target: "agent-coordination-acl.md"
    condition: when matching semantic ownership patterns against ACL claim patterns
last_updated: 2026-07-09
---

# Semantic Graph Service

## Context
RFC-0010 semantic graph state lives under `src/metagit/core/semantic/`.
The package follows the ACL/taskgraph style: pydantic models, path helpers,
file-backed JSON stores, service methods returning `T | Exception`, and JSONL
events under `.metagit/events/`.

## Steps
1. Start with focused tests under `tests/core/semantic/`.
2. Keep persistence in `SemanticGraphStore`; service code should orchestrate
   validation, upserts, lookups, and event emission.
3. Reuse `patterns_overlap` from `metagit.core.coordination.claim_service` for
   ownership/path matching. Do not duplicate glob logic.
4. Slugify human concept names in the service boundary, then let pydantic models
   enforce ids, repositories, and patterns.
5. Export new public service/result types from `metagit.core.semantic.__init__`.

## Gotchas
- `JsonListStore.load()` already returns `[]` for missing files; preserve that
  behavior in semantic store/service tests.
- Ownership repositories use `project/repo`; bare repo names and deeper paths
  should be rejected by the model layer.
- Whitespace-only patterns must fail validation after cleaning.
- GitNexus may report local index version mismatch in worktrees. Record the
  blocker and rerun `task gitnexus:analyze` before handoff.

## Verify
- [ ] `uv run pytest tests/core/semantic`
- [ ] `uv run ruff check src/metagit/core/semantic tests/core/semantic`
- [ ] `task qa:prepush`
- [ ] `task gitnexus:analyze`

## Debug
- Import errors usually mean `__init__.py` exports or a new module file is
  missing.
- False owner misses usually mean path/pattern arguments were reversed or
  normalized differently before calling `patterns_overlap`.
- Event failures should not block the core store path unless the task explicitly
  requires durable event semantics.

## Update Scaffold
- [ ] Update `.mex/ROUTER.md` "Current Project State" if the semantic graph
  surface changed.
- [ ] Update `CHANGELOG.md` for user-visible semantic graph behavior.
- [ ] Add docs/CLI/MCP modality entries only when those surfaces are exposed.

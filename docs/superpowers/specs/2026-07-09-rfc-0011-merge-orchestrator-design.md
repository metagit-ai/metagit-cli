# RFC-0011: Merge Orchestrator & Conflict Resolution — Design

**Status:** Draft  
**Date:** 2026-07-09  
**Series:** [ACL RFC series index](2026-07-09-acl-rfc-series-index.md)  
**Vision:** [agent-coordination.md](../../reference/agent-coordination.md) (RFC-0007 vision; original spec.md retired) § Integration Branches, Merge Orchestrator  
**Depends on:** RFC-0007 ACL; RFC-0008 completed nodes (preferred)  
**Plan:** [2026-07-09-rfc-0011-merge-orchestrator.md](../plans/2026-07-09-rfc-0011-merge-orchestrator.md)

## Summary

Orchestrate merges of completed agent branches into **integration branches** (not directly into long-lived feature branches), detect conflicts, record merge attempts, optionally hint/spawn merge-resolution agents, and run pluggable validation hooks (build/lint/test). This is CI-shaped coordination for autonomous agents, not a full CI product.

## Goals

- Integration branch naming/lifecycle tied to ACL `integration_branch` fields.
- Merge queue records: enqueue agent branch → attempt merge → success/fail/conflict.
- Conflict payload suitable for a merge-resolution agent dispatch hint.
- Pluggable validators (shell commands or taskfile targets) with recorded results.
- CLI/MCP status/retry; events `MergeSucceeded` / `MergeFailed` / `ConflictDetected`.

## Non-Goals

- Hosted CI replacement (GitHub Actions/GitLab CI remain external).
- Scheduler (RFC-0012) — merge orchestrator reacts to completed work, does not pick next coding task.
- Automatic force-push or remote protection bypass.
- SPA.

## Architecture

```text
Completed TaskNode / agent branch
        │
        ▼
 MergeOrchestrator
        ├── ensure integration branch
        ├── merge attempt (GitPython)
        ├── on conflict → ConflictRecord + dispatch hint
        └── validators (pluggable) before promoting integration → feature (optional step)
```

**Package:** `src/metagit/core/merge/`

**Policy (locked from vision):** agents merge into `integration/<topic>`; only after validation may integration merge into feature. v1 may implement agent→integration fully and treat integration→feature as explicit operator/agent step.

## Interfaces

### CLI

```bash
metagit merge enqueue --repository P/R --branch agent/… --into integration/… [--node-id …]
metagit merge status [--repository P/R] [--json]
metagit merge retry --merge-id …
metagit merge integrate --merge-id …   # attempt merge
metagit merge promote --integration integration/… --into feature/…   # optional gated step
```

### MCP

`metagit_merge_enqueue`, `metagit_merge_status`, `metagit_merge_retry`, `metagit_merge_integrate`

## Persistence

```text
.metagit/merges/
  queue.json
  <merge_id>.json
```

## Events

`MergeEnqueued`, `MergeSucceeded`, `MergeFailed`, `ConflictDetected`, `ValidationFailed` — `source=merge`.

## Acceptance

- Enqueue + integrate clean branch succeeds and records result.
- Conflicting branch yields conflict record + non-zero/structured error without corrupting integration.
- Validator failure blocks promote (if promote implemented).
- Tests with temporary git repos; docs + modality.

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| ACL branches/worktrees; 0008 completion signals | 0012 (backpressure), 0013 |

## Open questions

1. Default validator set: none vs `task test` discovery?
2. Should conflict resolution auto-allocate ACL for merge agent?

**Recommendation:** validators opt-in via config; conflict path emits dispatch hints including optional `acl_commands`, no auto-allocate in v1.

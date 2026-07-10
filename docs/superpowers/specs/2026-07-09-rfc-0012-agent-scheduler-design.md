# RFC-0012: Distributed Agent Scheduler — Design

**Status:** Draft  
**Date:** 2026-07-09  
**Series:** [ACL RFC series index](2026-07-09-acl-rfc-series-index.md)  
**Vision:** [agent-coordination.md](../../reference/agent-coordination.md) (RFC-0007 vision; original spec.md retired) § Scheduling  
**Depends on:** RFC-0008 ready set; RFC-0011 optional for merge backpressure  
**Plan:** [2026-07-09-rfc-0012-agent-scheduler.md](../plans/2026-07-09-rfc-0012-agent-scheduler.md)

## Summary

Choose **which ready task node should run next** using priority, dependency order, repository affinity, and simple cost/runtime estimates. The scheduler **does not launch models**; it returns a dispatch plan (and optional ACL/context hints) for an orchestrator to execute.

## Goals

- Ready queue derived from task graph + policy weights.
- Factors (v1 subset): priority, dependency order, repository affinity (prefer warm worktrees), estimated token cost / runtime (heuristics or manifest fields).
- CLI/MCP: `schedule next`, `schedule status`, `schedule policy show|set` (local JSON policy).
- Integrate with `metagit agent dispatch-plan` output shape where practical.
- Respect merge-queue backpressure when RFC-0011 is present (optional soft dependency).

## Non-Goals

- Multi-host cluster scheduling / GPU brokers.
- Embedding a specific agent runtime (Cursor/Claude/Hermes launchers stay external).
- Full AOS (RFC-0013).
- Guaranteed optimal scheduling.

## Architecture

```text
TaskGraphService.ready()
        │
        ▼
 SchedulerService + SchedulePolicy
        ├── score nodes
        ├── optional merge-queue pressure
        └── emit ScheduleDecision → dispatch-plan fields
```

**Package:** `src/metagit/core/scheduler/`

## Interfaces

### CLI

```bash
metagit schedule policy show|--json
metagit schedule next [--graph-id …] [--limit 1] [--json]
metagit schedule status [--json]
```

### MCP

`metagit_schedule_next`, `metagit_schedule_status`, `metagit_schedule_policy`

### Decision payload (proposed)

`node_id`, `score`, `reasons[]`, `dispatch_hints`, `acl_commands?`, `compile_command?`

## Persistence

```text
.metagit/schedule/
  policy.json
  decisions.jsonl
```

## Events

`ScheduleDecision`, `ScheduleSkipped` — `source=scheduler`.

## Acceptance

- With two ready nodes, policy priority selects the higher one deterministically.
- Affinity prefers node whose repo already has an active worktree for the agent pool (configurable).
- No git mutation from scheduler itself.
- Tests for scoring; docs + modality.

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| RFC-0008; optional 0009/0011 | RFC-0013 |

## Decisions (locked)

1. **Policy scope:** per-workspace `policy.json` with optional `graph_overrides[graph_id]`.
2. **Fairness:** optional `weights.fairness` (default `0.0`); when enabled, bias toward repos under-represented in recent `decisions.jsonl`.
3. **Node fields:** additive optional `TaskNode.priority: int = 0` and `TaskNode.estimated_tokens: int | None` (fallback `context_budget`, then `1000`).
4. **Tie-break:** higher score → lower effective tokens → lexicographic `node_id`.
5. **Merge backpressure:** soft penalty by default; optional `skip_on_merge_pressure` emits skipped decision instead of hard failure.

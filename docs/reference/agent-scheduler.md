---
title: Agent Scheduler
---

<!-- modality:agent_scheduler -->

# Distributed Agent Scheduler

RFC-0012 scores ready task-graph nodes and returns the next schedule decision
plus dispatch hints. It does **not** launch models and does **not** mutate git.

The scheduler is deliberately advisory. An orchestrator (human or agent) still
runs ACL allocate/lease/worktree, context compile, and the actual agent runtime.

## Model

```text
.metagit/
  schedule/
    policy.json
    decisions.jsonl
  events/
    scheduler.jsonl
```

`TaskNode` may carry additive optional fields used by scoring:

| Field | Default | Meaning |
|-------|---------|---------|
| `priority` | `0` | Higher values win when other factors are equal |
| `estimated_tokens` | unset | Falls back to `context_budget`, then `1000` |

Default scoring factors:

| Factor | Default weight | Meaning |
|--------|----------------|---------|
| priority | 1.0 | Higher `TaskNode.priority` wins |
| affinity | 0.5 | Prefer repos with an active ACL worktree |
| cost | 0.25 | Prefer lower effective token estimates |
| fairness | 0.0 | Optional bias toward under-scheduled repos |

Tie-break is deterministic: higher score → lower effective tokens →
lexicographic `node_id`.

Optional soft merge backpressure uses RFC-0011 queue depth. When a repository
has `queued|running` merges ≥ `merge_queue_threshold` (default 3), the node
score is reduced by `merge_pressure_penalty`. With `skip_on_merge_pressure`,
the scheduler emits a skipped decision instead of selecting that node as next.

Policy is per-workspace (`policy.json`) with optional `graph_overrides[graph_id]`.

## CLI

```bash
# Inspect / update local schedule policy
metagit schedule policy show --json
metagit schedule policy set --priority 2 --affinity 0.5 --json
metagit schedule policy set --graph-id g1 --priority 3 --json

# Choose the next ready node(s)
metagit schedule next [--graph-id …] [--limit 1] --json

# Ready count, recent decisions, merge pressure summary
metagit schedule status --json
```

Use `--definition path/to/.metagit.yml` when running outside the manifest root.

## MCP Tools

When the workspace gate is ACTIVE:

| Tool | Arguments | Purpose |
|------|-----------|---------|
| `metagit_schedule_next` | optional `graph_id`, `limit` | Score ready nodes and return decision(s). |
| `metagit_schedule_status` | optional `recent` | Policy + ready count + recent decisions. |
| `metagit_schedule_policy` | `action=show\|set` plus optional weight fields | Read or update local policy. |

The MCP surface returns the same JSON shapes as the core service
(`model_dump(mode="json")`) and uses the same persistence under `.metagit/`.

## Decision payload

Each decision includes:

- `node_id`, `graph_id`, `score`, `reasons[]`
- `dispatch_hints` (title/project/repository/agent_id/priority)
- optional `acl_commands` copied from the task node ACL binding
- optional `compile_command` when project + repository are known
- `skipped` when merge pressure skip mode applies

## Events

Scheduler lifecycle events append to `.metagit/events/scheduler.jsonl` and
appear in `metagit context events` with `source: scheduler`.

Event kinds:

- `ScheduleDecision`
- `ScheduleSkipped`

## Safety Boundaries

- No git mutation (no checkout, merge, push, or ACL allocate).
- No model/runtime launch; decisions are hints for an external orchestrator.
- Merge backpressure is soft and optional; RFC-0011 need not be present.
- Affinity uses active ACL worktrees when available; missing worktree data is
  treated as no affinity boost.
- Guaranteed optimal scheduling is out of scope.

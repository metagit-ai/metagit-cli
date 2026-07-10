---
title: Agent Operating System
---

<!-- modality:aos_status -->

# Agent Operating System (RFC-0013)

Composition façade over ACL, task graph, and optional RFC-0009–0012
subsystems. AOS does **not** add new engines or persistence. It answers
“what is the coordination OS doing?” and “what should run next?”

Git remains the source of truth for code. AOS never launches models.

## Commands

Primary group `aos`; alias group `coord` (identical behavior).

```bash
metagit aos status [--json]
metagit aos doctor [--json] [--fix] [--yes]
metagit aos next [--json] [--commit] [--apply-hints] [--agent-id …] [--graph-id …]

# aliases
metagit coord status|doctor|next …
```

### status

Read-only snapshot. Each subsystem section includes `available: bool` plus
summary counts. Missing optional RFCs degrade to `available: false`.

### doctor

Report-only by default (`findings[]`, `suggested_commands[]`).

`--fix` requires `--yes`. Allowed mutations are safe ACL GC only:

1. `LeaseService.list()` (expire-on-list side effect)
2. `WorktreeService.gc()`

Never releases claims, cancels merges, or mutates tasks.

### next

Default is **preview** — ranks ready work without appending
`.metagit/schedule/decisions.jsonl`.

| Flag | Effect |
|------|--------|
| `--commit` | Delegate to `SchedulerService.next()` (records decision) |
| `--apply-hints` | Run ACL allocate/lease/worktree/claim APIs (requires `--agent-id`) |

`--apply-hints` never runs context compile (returns `compile_command` only)
and never launches models.

## MCP

ACTIVE-gated. Alias tools share handlers with primary tools.

| Primary | Alias |
|---------|-------|
| `metagit_aos_status` | `metagit_coord_status` |
| `metagit_aos_doctor` | `metagit_coord_doctor` |
| `metagit_aos_next` | `metagit_coord_next` |

Doctor: `fix` + `confirm` mirrors CLI `--fix --yes`.
Next: `commit`, `apply_hints`, `agent_id`, `graph_id`, `limit`.

## Control loop

```text
aos next [--commit]
  → context compile (hint / separate command)
  → ACL bind (hints or --apply-hints)
  → agent work
  → task complete
  → merge enqueue
```

See also: [agent-coordination.md](agent-coordination.md),
[agent-scheduler.md](agent-scheduler.md),
[task-graph.md](task-graph.md).

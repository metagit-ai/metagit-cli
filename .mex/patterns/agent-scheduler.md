---
name: agent-scheduler
description: Implementing or extending RFC-0012 distributed agent scheduler scoring, policy, CLI/MCP, and events.
triggers:
  - "agent scheduler"
  - "RFC-0012"
  - "SchedulerService"
  - "metagit schedule"
  - "preview_next"
  - ".metagit/schedule"
edges:
  - target: "../context/conventions.md"
    condition: when writing or reviewing scheduler code
  - target: "task-graph-intent.md"
    condition: when consuming TaskGraphService.ready()
  - target: "merge-orchestrator.md"
    condition: when wiring soft merge-queue backpressure
  - target: "aos-composition.md"
    condition: when AOS next preview/commit uses scheduler APIs
last_updated: 2026-07-10
---

# Agent Scheduler

## Context
RFC-0012 lives under `src/metagit/core/scheduler/`.
It scores ready task nodes and returns schedule decisions. It never launches
models and never mutates git.

## Steps
1. Keep scoring pure in `scoring.py` with deterministic tie-break:
   higher score → lower effective tokens → lexicographic `node_id`.
2. Persist policy/decisions under `.metagit/schedule/`; events under
   `.metagit/events/scheduler.jsonl`.
3. Share ranking via `_select_next(..., persist=True|False)`:
   - `next()` persists decisions + events
   - `preview_next()` ranks the same way but does **not** append JSONL or emit events
     (used by RFC-0013 `metagit aos next` default preview)
4. Inject `ready_fn` / `worktrees_fn` / `merge_status_fn` in tests; production
   defaults soft-depend on taskgraph, worktrees, and merge.
5. Expose thin CLI `metagit schedule` and ACTIVE-gated MCP
   `metagit_schedule_*` tools sharing `SchedulerService`.
6. Register modality `agent_scheduler` in `scripts/modality-parity.yml`.

## Gotchas
- Optional `TaskNode.priority` / `estimated_tokens` are additive; default
  priority is `0` and tokens fall back to `context_budget` then `1000`.
- Merge backpressure is soft by default; `skip_on_merge_pressure` emits a
  skipped decision rather than failing hard.
- Do not change `next()` persistence semantics when editing preview paths —
  AOS and schedule CLI both rely on the split.
- Prefer GitNexus CLI (`gitnexus impact`) when MCP LadybugDB versions mismatch.

## Verify
- `uv run pytest tests/core/scheduler tests/cli/commands/test_schedule_cli.py tests/core/mcp/test_schedule_tools.py -q`
- `task qa:prepush`

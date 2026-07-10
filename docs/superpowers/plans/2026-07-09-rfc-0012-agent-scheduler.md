# RFC-0012 Distributed Agent Scheduler — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Score ready task nodes and return the next schedule decision + dispatch hints without launching models or mutating git.

**Architecture:** New `src/metagit/core/scheduler/` reads the taskgraph ready set + local `policy.json`, scores nodes (priority, affinity, simple cost), optionally soft-checks merge queue depth, appends decisions JSONL, exposes CLI/MCP. Scheduler never launches agents and never mutates git.

**Tech Stack:** Pydantic, Click, MCP, pytest. Reuse `TaskGraphService.ready()`, optional `MergeOrchestrator.status()`, optional `WorktreeService.list()` for affinity.

**Design:** [2026-07-09-rfc-0012-agent-scheduler-design.md](../specs/2026-07-09-rfc-0012-agent-scheduler-design.md)  
**Series:** [acl-rfc-series-index](../specs/2026-07-09-acl-rfc-series-index.md)  
**Branch:** `feat/rfc-0012-agent-scheduler` (worktree `.worktrees/rfc-0012`)

## Locked decisions

1. **Policy scope:** per-workspace `policy.json` with optional `graph_overrides[graph_id]` weight overrides.
2. **Fairness:** optional `weights.fairness` (default `0.0` / off). When > 0, prefer repos with fewer recent decisions in `decisions.jsonl` (simple round-robin bias). Not MVP-critical; implement the weight hook so tests can set it.
3. **Priority / cost on nodes:** additive optional fields on `TaskNode`: `priority: int = 0` (higher wins), `estimated_tokens: int | None = None` (fallback: `context_budget`, then default `1000`).
4. **Tie-break (deterministic):** higher score → lower effective tokens → lexicographic `node_id`.
5. **Merge backpressure:** soft. If queued+running merges for a node's repository ≥ `merge_queue_threshold` (default `3`), apply `merge_pressure_penalty` to that node's score. If the winning node is still over threshold, emit decision with a pressure reason (do not hard-block unless `skip_on_merge_pressure: true`).
6. **GitNexus:** use CLI (`gitnexus impact` / `task gitnexus:analyze`) when MCP LadybugDB is version-mismatched.

## Global constraints

- Modality: CLI + MCP + core + docs/skills; no SPA; no `/v3/ops`.
- Persistence: `.metagit/schedule/{policy.json,decisions.jsonl}` + events `.metagit/events/scheduler.jsonl`.
- No git mutation from scheduler.
- Works with taskgraph only; merge/worktree integrations are optional soft deps.
- Before editing shared symbols: CLI impact; always `task qa:prepush` before hand-off.
- Implement on feature branch, not `main`.

## Out of scope

Multi-host/GPU brokers, embedding agent runtimes, guaranteed optimal scheduling, AOS façade (0013), SPA, SQLite.

## File map (create)

| Path | Responsibility |
|------|----------------|
| `src/metagit/core/scheduler/__init__.py` | Exports |
| `src/metagit/core/scheduler/models.py` | Policy, decision, status, events |
| `src/metagit/core/scheduler/paths.py` | `.metagit/schedule/` + events path |
| `src/metagit/core/scheduler/store.py` | Load/save policy + append decisions JSONL |
| `src/metagit/core/scheduler/scoring.py` | Pure deterministic score + tie-break |
| `src/metagit/core/scheduler/service.py` | `next` / `status` / `policy` orchestration |
| `src/metagit/core/scheduler/events.py` | Append `source=scheduler` events |
| `src/metagit/cli/commands/schedule.py` | Click group `schedule` |
| `tests/core/scheduler/` | Unit tests |
| `tests/cli/commands/test_schedule_cli.py` | CLI tests |
| `tests/core/mcp/test_schedule_tools.py` | MCP tests |
| `docs/reference/agent-scheduler.md` | Operator reference |
| `.mex/patterns/agent-scheduler.md` | Recurring runbook |

## File map (modify)

- `src/metagit/core/taskgraph/models.py` — optional `priority`, `estimated_tokens` on `TaskNode`
- `src/metagit/cli/main.py` — register `schedule_group`
- MCP `tool_registry.py` + `runtime.py` — schedule tools
- `event_service.py` — merge `source=scheduler`
- `scripts/modality-parity.yml` — `agent_scheduler`
- docs/skills/AGENTS/llms/mkdocs/CHANGELOG/ROUTER/series index

## Scoring formula

```text
effective_tokens = node.estimated_tokens or node.context_budget or 1000
cost_score = 1.0 / (1.0 + effective_tokens / 1000.0)
affinity = 1.0 if repository has an active worktree else 0.0
fairness = 1.0 if repo under-represented in recent decisions else 0.0  # only if weight > 0
raw = (
  w.priority * float(priority)
  + w.affinity * affinity
  + w.cost * cost_score
  + w.fairness * fairness
)
if merge_pressure and not skip: raw -= merge_pressure_penalty
score = round(raw, 6)
```

---

### Task 1: Models + paths + store + TaskNode fields

**Files:**
- Create: `src/metagit/core/scheduler/{__init__,models,paths,store}.py`
- Modify: `src/metagit/core/taskgraph/models.py` (`priority`, `estimated_tokens`)
- Test: `tests/core/scheduler/test_models.py`, `tests/core/scheduler/test_store.py`

- [ ] **Step 1: Write failing tests** for `SchedulePolicy` defaults, policy round-trip, decision append, and `TaskNode.priority` default `0`.
- [ ] **Step 2: Run — expect fail**.
- [ ] **Step 3: Implement**

`SchedulePolicy` fields:
- `weights`: `{priority: 1.0, affinity: 0.5, cost: 0.25, fairness: 0.0}`
- `merge_queue_threshold: int = 3`
- `merge_pressure_penalty: float = 2.0`
- `skip_on_merge_pressure: bool = False`
- `graph_overrides: dict[str, ScheduleWeightOverrides] = {}`

`ScheduleDecision`: `decision_id`, `at`, `graph_id`, `node_id`, `score`, `reasons: list[str]`, `dispatch_hints: dict`, `acl_commands: list[str]`, `compile_command: str | None`, `skipped: bool = False`

Paths: `schedule_root`, `policy_file`, `decisions_file`, `events_file`.

Store: `load_policy` / `save_policy` / `append_decision` / `list_decisions` with file lock. `T | Exception`.

- [ ] **Step 4: Tests pass**.
- [ ] **Step 5: Commit** `feat(scheduler): add models and JSON store for RFC-0012`

---

### Task 2: Scoring (pure functions)

**Files:** create `scoring.py`; test `test_scoring.py`

- [ ] **Step 1: Failing tests**
  - higher priority wins when other factors equal
  - affinity boosts warm-worktree repo
  - lower estimated_tokens scores higher on cost weight
  - tie-break by `node_id` when scores equal
- [ ] **Step 2: Implement** `score_node(...)` and `rank_candidates(...)`.
- [ ] **Step 3: Tests pass**.
- [ ] **Step 4: Commit** `feat(scheduler): deterministic ready-node scoring`

---

### Task 3: SchedulerService.next + status + events

**Files:** create `service.py`, `events.py`; tests `test_service.py`

- [ ] **Step 1: Failing tests**
  - `next` picks higher-priority ready node; persists decision; emits `ScheduleDecision`
  - empty ready set → empty list / no crash
  - `status` returns policy summary + recent decisions + ready counts
- [ ] **Step 2: Implement `SchedulerService`**
  - `policy_show` / `policy_set` (partial update)
  - `next(graph_id=None, limit=1)` → list[ScheduleDecision]
  - Build `dispatch_hints` with node title/repo/project; `acl_commands` from `node.acl.acl_commands` when present; `compile_command` when project+repository known: `metagit context compile --project P --repo R --task-id NODE`
  - Optional injectables: `ready_fn`, `worktrees_fn`, `merge_status_fn` for tests
- [ ] **Step 3: Tests pass**.
- [ ] **Step 4: Commit** `feat(scheduler): schedule next/status service`

---

### Task 4: Soft merge backpressure

**Files:** extend `service.py` / `scoring.py`; test `test_merge_pressure.py`

- [ ] **Step 1: Failing tests**
  - when repo A has ≥ threshold queued merges, prefer ready node on repo B
  - with `skip_on_merge_pressure=True` and only pressured repos ready → `ScheduleSkipped` / skipped decision with reason
- [ ] **Step 2: Implement** using optional `merge_status_fn` returning merge rows (`repository`, `status` in `queued|running` count toward depth).
- [ ] **Step 3: Tests pass**.
- [ ] **Step 4: Commit** `feat(scheduler): soft merge-queue backpressure`

---

### Task 5: CLI + MCP + event feed + modality + docs

**Files:** CLI/MCP/docs/parity/CHANGELOG/ROUTER/index/skills

- [ ] **Step 1: CLI** `metagit schedule policy show|set`, `next`, `status` with `--json`.
- [ ] **Step 2: MCP** `metagit_schedule_next`, `metagit_schedule_status`, `metagit_schedule_policy` (ACTIVE-gated).
- [ ] **Step 3: Wire** `event_service` `source=scheduler`; modality `agent_scheduler`; reference doc; skill markers; mkdocs; AGENTS/llms; series index → Implemented.
- [ ] **Step 4: Tests** CLI + MCP.
- [ ] **Step 5: Commit** `feat(scheduler): CLI/MCP parity and operator docs for RFC-0012`

---

### Task 6: Closeout

- [ ] **Step 1:** `task qa:prepush` until green.
- [ ] **Step 2:** Update `.mex/ROUTER.md` + pattern; bump series index.
- [ ] **Step 3:** `task gitnexus:analyze`.
- [ ] **Step 4:** Commit any closeout docs `docs: RFC-0012 scheduler closeout`.

## Acceptance checklist

- [ ] Higher priority wins deterministically.
- [ ] Affinity prefers repos with active worktrees.
- [ ] Scheduler performs no git mutations.
- [ ] Works with taskgraph only (0011 optional).
- [ ] Parity + docs updated.
- [ ] `task qa:prepush` green.

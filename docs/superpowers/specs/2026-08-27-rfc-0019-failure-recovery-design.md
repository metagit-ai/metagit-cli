# RFC-0019: Failure Recovery & Control-Loop Resilience — Design

**Status:** Proposed  
**Date:** 2026-08-27  
**Series:** [Agent Reliability series index](2026-08-27-agent-reliability-series-index.md)  
**Depends on:** RFC-0013 (AOS), RFC-0007 (ACL), RFC-0008 (task graph), optionally RFC-0011 (merge), RFC-0012 (scheduler), RFC-0017 (harness heartbeat alignment)  
**Plan:** (pending)

## Summary

Extend the existing AOS composition façade (`AosService.doctor`, CLI `metagit aos doctor`) with **actionable recovery recipes** and add a gated **`metagit aos recover`** command for agent-scoped crash recovery. Recovery reuses existing ACL, task graph, and merge services — no new engines or persistence backends. Mutations stay behind explicit confirmation (`--yes`); destructive actions (claim release, merge cancel) require **additional explicit flags**. Emit recovery and heartbeat activity into the shared coordination events feed (`metagit context events`, `source=aos`).

## Goals

1. **Richer doctor findings** — detect stale leases, orphan worktrees, orphan claims, stuck `running` task nodes, merge-queue pressure, and harness/run drift (when RFC-0017 present); attach structured **recovery recipes** with copy-paste CLI and safe-default hints.
2. **`metagit aos recover --agent-id … --yes`** — agent-scoped recovery applying **safe GC + status transitions only** by default (lease expiry side effects, worktree GC, reset stuck tasks to schedulable state).
3. **Heartbeat / lease renewal helpers** — `metagit aos heartbeat --agent-id …` renews active ACL leases for the agent; align TTL policy with RFC-0017 harness heartbeat when both are in use.
4. **Event emission** — append typed events to `.metagit/events/aos.jsonl`; surface via `WorkspaceEventService` as `source=aos`.
5. **Safety invariants** — recover never silently releases claims or cancels/aborts merges; those paths require `--release-orphan-claims` and `--cancel-stale-merges` respectively.
6. **Parity** — CLI, MCP, skill (`metagit-aos`), docs (`aos.md`, `agent-coordination.md`), modality registry.

## Non-Goals

- A new orchestrator, crash detector daemon, or background reaper process.
- Automatic recovery on every `aos next` or scheduler tick (operators/agents invoke doctor/recover explicitly).
- Replacing RFC-0017 harness heartbeat/run lifecycle (AOS heartbeat is ACL-lease scoped; harness heartbeat remains run-scoped).
- Force-pushing branches, git history rewrite, or remote protection bypass.
- Policy engine integration (RFC-0022) — recover actions are allowlisted, not policy-evaluated in v1.
- Multi-workspace federation recovery (RFC-0023).

## Decisions (locked)

| # | Decision |
|---|----------|
| D1 | **Composition-only** — extend `AosService`; delegate mutations to existing 0007/0008/0011 services. |
| D2 | **Doctor default stays report-only** — no mutation without `--fix --yes`. `--fix` scope unchanged in spirit: safe ACL GC only (lease expire-on-list + `worktree gc`). |
| D3 | **`recover` is a separate command** — not folded into `doctor --fix`. Requires `--agent-id` and `--yes`. Default actions are safe GC + task status transitions only. |
| D4 | **Claim release and merge cancel are opt-in flags** on `recover` (`--release-orphan-claims`, `--cancel-stale-merges`). Never implied by `--yes` alone. |
| D5 | **Stuck task reset** transitions `running → ready` (not `cancelled`) when the node's bound agent has no active lease; emits `TaskGraphEvent` via existing store. |
| D6 | **Events** append to `.metagit/events/aos.jsonl`; `WorkspaceEventService` includes `source=aos`. Subsystem events (acl, taskgraph, merge) remain authoritative for domain semantics. |
| D7 | **Heartbeat** renews all **active** ACL leases owned by `--agent-id`; does not acquire new leases or create worktrees. |
| D8 | **JSON-first** under `METAGIT_AGENT_MODE=true`; human text output mirrors existing `aos doctor` style. |
| D9 | **Modality** extends existing `aos_status` feature id (no new engine modality). |

## Architecture

```text
metagit aos  doctor|recover|heartbeat
                    │
                    ▼
               AosService
     ┌──────────────┼──────────────┐
     ▼              ▼              ▼
 RecoveryAnalyzer  RecoveryExecutor  HeartbeatHelper
 (extends _analyze) (recover path)   (lease renew)
     │              │              │
     ▼              ▼              ▼
 collectors    LeaseService     LeaseService.renew
 (existing)    WorktreeService.gc
               TaskGraphService (reset running→ready)
               ClaimService.release (flagged)
               MergeOrchestrator.cancel (flagged)
     │
     ▼
 AosEventStore → WorkspaceEventService (source=aos)
```

**Package additions (proposed):**

| Module | Role |
|--------|------|
| `src/metagit/core/aos/recovery.py` | Detection rules + recipe builders (pure functions over collector snapshots) |
| `src/metagit/core/aos/events.py` | `AosEventStore` — JSONL append/list |
| `src/metagit/core/aos/service.py` | Extend `doctor()`, add `recover()`, `heartbeat()` |

Approach locked: **thin aggregator** — same pattern as RFC-0013; inject `recover_fn` / `heartbeat_fn` for tests.

## Detection rules (doctor / recover analyze phase)

Rules run against the same subsystem snapshots `DefaultSubsystemCollector` already produces, plus lightweight cross-subsystem joins (no new stores).

| Code | Severity | Condition | Subsystem |
|------|----------|-----------|-----------|
| `stale_lease` | warning | `leases_expired > 0` | acl |
| `orphan_worktree_risk` | warning | active worktree record whose `lease_id` not in active leases, or checkout path missing | acl |
| `orphan_claim` | warning | active claim whose `agent_id` has no active lease on the same `repository` | acl |
| `stuck_running_task` | warning | task node `status=running` and (`agent_id` has no active lease OR node `updated_at` older than configurable staleness, default 2h) | taskgraph |
| `blocked_tasks` | warning | `blocked > 0` | taskgraph |
| `empty_ready_set` | info | `ready == 0` | taskgraph |
| `merge_pressure` | warning | queued + running ≥ threshold (default 3) | merge |
| `stale_merge_running` | warning | merge record `status=running` with `updated_at` older than threshold (default 1h) — report only unless `--cancel-stale-merges` | merge |
| `subsystem_unavailable` | info | optional RFC package missing | * |

Each finding MAY include `affected_ids: list[str]` (lease ids, worktree ids, node ids, merge ids) for agent-scoped filtering in `recover`.

## Recovery recipes

Doctor output gains `recovery_recipes[]` alongside existing `suggested_commands[]`. Recipes are structured; suggested_commands remain flat CLI strings for backward compatibility.

```python
class AosRecoveryRecipe(BaseModel):
    code: str                    # mirrors finding code, e.g. orphan_worktree_risk
    action: str                  # stable id, e.g. gc_worktrees
    description: str
    command: str                 # copy-paste CLI
    safe_default: bool           # True → eligible for recover --yes without extra flags
    requires_flag: Optional[str] # e.g. release_orphan_claims, cancel_stale_merges
    subsystem: str
```

**Example recipes (doctor report-only):**

| action | safe_default | command template |
|--------|--------------|------------------|
| `expire_leases` | yes | `metagit lease list --agent-id {agent_id} --json` (expire-on-list side effect) |
| `gc_worktrees` | yes | `metagit worktree gc` |
| `recover_agent` | yes | `metagit aos recover --agent-id {agent_id} --yes` |
| `reset_stuck_task` | yes | included in `aos recover` default bundle |
| `release_orphan_claims` | **no** | `metagit aos recover --agent-id {agent_id} --yes --release-orphan-claims` |
| `cancel_stale_merge` | **no** | `metagit aos recover --agent-id {agent_id} --yes --cancel-stale-merges` |
| `renew_leases` | yes | `metagit aos heartbeat --agent-id {agent_id}` |

## Interfaces

### CLI

Primary group `aos`; alias group `coord` (identical).

```bash
# existing — extended JSON shape (recovery_recipes[])
metagit aos doctor [--json] [--fix] [--yes] [--agent-id …]

# new
metagit aos recover --agent-id AGENT --yes \
  [--release-orphan-claims] \
  [--cancel-stale-merges] \
  [--task-staleness 2h] \
  [--json]

metagit aos heartbeat --agent-id AGENT [--ttl 30m] [--json]

# aliases
metagit coord doctor|recover|heartbeat …
```

**`doctor` changes:**

- `--agent-id` optional filter: findings/recipes scoped to one agent when set; omit for workspace-wide report.
- `--fix --yes` behavior unchanged: workspace-wide safe GC via `_default_fix()` (lease expire-on-list + `WorktreeService.gc()`).
- New field `recovery_recipes[]` in JSON output.

**`recover` behavior:**

- **Requires** `--agent-id` and `--yes`. Without `--yes` → error (same pattern as `doctor --fix`).
- **Default bundle** (safe GC + status transitions):
  1. `LeaseService.list(agent_id=…)` — expire stale leases for agent.
  2. `WorktreeService.gc()` — destroys agent worktrees whose lease is gone (existing gc logic; filter applied actions to agent in result).
  3. For each `stuck_running_task` where `node.agent_id == agent_id`: transition `running → ready` via new `TaskGraphService.requeue(node_id)` (thin wrapper over internal status set + `TaskRequeued` event).
- **Never** in default bundle: claim release, merge cancel, branch release, task cancel/complete.
- **`--release-orphan-claims`**: `ClaimService.release` for active claims matching agent with no active lease on repository.
- **`--cancel-stale-merges`**: cancel merge queue rows in `running`/`queued` state tied to agent branches for that agent (via existing merge service cancel API if present; otherwise add minimal `MergeOrchestrator.cancel(merge_id)` — report-only until flag set).
- Returns `AosRecoverResult`: `{generated_at, agent_id, applied[], skipped[], findings[], recovery_recipes[]}`.

**`heartbeat` behavior:**

- List active leases for `--agent-id`; call `LeaseService.renew` for each (default TTL from appconfig / `DEFAULT_LEASE_TTL`).
- Append `HeartbeatRecorded` aos event with `{agent_id, lease_ids[], ttl}`.
- If RFC-0017 harness run is active for the agent (optional cross-check via `harness.runs` or routing ledger), docs recommend calling **both** `metagit harness heartbeat` and `metagit aos heartbeat` during long work.

### MCP

ACTIVE-gated. Alias tools share handlers.

| Primary | Alias | Purpose |
|---------|-------|---------|
| `metagit_aos_doctor` | `metagit_coord_doctor` | Extended findings + `recovery_recipes`; `agent_id` filter; `fix` + `confirm` unchanged |
| `metagit_aos_recover` | `metagit_coord_recover` | `agent_id`, `confirm`, optional `release_orphan_claims`, `cancel_stale_merges` |
| `metagit_aos_heartbeat` | `metagit_coord_heartbeat` | `agent_id`, optional `ttl` |

### Models (proposed additions to `metagit.core.aos.models`)

```python
class AosRecoveryRecipe(BaseModel): ...

class AosRecoverResult(BaseModel):
    generated_at: str
    agent_id: str
    applied: list[str]       # e.g. lease_expired:…, worktree_destroyed:…, task_requeued:…
    skipped: list[str]       # e.g. merge_cancel_skipped:needs_flag
    findings: list[AosFinding]
    recovery_recipes: list[AosRecoveryRecipe]

class AosHeartbeatResult(BaseModel):
    generated_at: str
    agent_id: str
    renewed_lease_ids: list[str]
    ttl: str
```

Extend `AosDoctorResult` with `recovery_recipes: list[AosRecoveryRecipe]`.

### Skill & docs

- Update bundled **`metagit-aos`**: control-loop section adds doctor → recover → heartbeat; when to use explicit claim/merge flags.
- Update **`docs/reference/aos.md`**: recover + heartbeat commands; doctor recipe shape.
- Update **`docs/reference/agent-coordination.md`**: crash recovery subsection under Agent Operating System; link RFC-0019.
- Update **`docs/agents-quickstart.md`**: one-line pointer under Health (“after crash: `aos recover --agent-id … --yes`”).

## Persistence

No new AOS state files. Recovery reads/writes existing stores:

| Store | Path | Recover interaction |
|-------|------|---------------------|
| Leases | `.metagit/leases/leases.json` | expire-on-list, renew (heartbeat) |
| Worktrees | `.metagit/worktrees/worktrees.json` + disk | `gc()` / `destroy` |
| Claims | `.metagit/claims/claims.json` | `release` only with `--release-orphan-claims` |
| Task graph | `.metagit/tasks/*.json` | `requeue` (`running → ready`) |
| Merge queue | `.metagit/merges/` | cancel only with `--cancel-stale-merges` |
| AOS events | `.metagit/events/aos.jsonl` | append-only |

Optional appconfig (`.metagit.yml` / appconfig) keys:

```yaml
aos:
  recovery:
    task_staleness: 2h
    merge_staleness: 1h
    merge_pressure_threshold: 3
  heartbeat:
    default_ttl: 30m
```

## Events

### AosEventStore

Append-only JSONL at `.metagit/events/aos.jsonl`.

| type | When | payload (representative) |
|------|------|--------------------------|
| `DoctorReported` | doctor (no fix) | `{finding_count, agent_id?}` |
| `DoctorFixApplied` | doctor `--fix --yes` | `{fixed: [...]}` |
| `RecoveryApplied` | recover `--yes` | `{agent_id, applied, flags}` |
| `HeartbeatRecorded` | heartbeat | `{agent_id, lease_ids, ttl}` |
| `RecoverySkipped` | recover declined action | `{agent_id, reason, requires_flag?}` |

Wire into `WorkspaceEventService.list_events()`:

```python
WorkspaceEvent(source="aos", kind=event.type, id=event.event_id, data=payload)
```

Subsystem events (`LeaseExpired`, `WorktreeDestroyed`, `TaskRequeued`, etc.) continue to emit from their respective stores as today — aos events are an audit overlay for operator dashboards polling `metagit context events`.

## Task graph addition

Add minimal API to RFC-0008 service (used only via recover):

```python
def requeue(self, node_id: str, *, graph_id: str | None = None, reason: str = "recovery") -> TaskNode | Exception:
    """Transition running → ready when dependencies allow; emit TaskRequeued."""
```

Validation: only from `running`; if dependencies not satisfied, transition to `pending` instead (match `compute_ready_ids` semantics). Never from `completed`/`cancelled`.

## Acceptance

- `metagit aos doctor --json` returns `recovery_recipes[]` with at least one recipe per detected issue class in fixture workspaces.
- Doctor without `--fix` never mutates; `--fix` without `--yes` errors; `--fix --yes` only performs lease expire + worktree gc (unchanged).
- `metagit aos recover --agent-id X --yes` without extra flags: expires agent leases, GCs orphan worktrees, requeues stuck running tasks for agent X; **does not** release claims or cancel merges.
- `recover` without `--yes` errors; without `--agent-id` errors.
- `--release-orphan-claims` and `--cancel-stale-merges` are required for those respective mutations; recover result lists skipped actions when findings exist but flags absent.
- `metagit aos heartbeat --agent-id X` renews active leases; fails clearly when none active.
- Events appear in `.metagit/events/aos.jsonl` and `metagit context events --json` with `source=aos`.
- Integration test: simulate agent crash mid-lease (acquire lease + start task + exit without release); `doctor` reports findings; `recover --yes` restores schedulable state; second agent can `aos next`.
- Integration test: recover with orphan claims does **not** release until `--release-orphan-claims`.
- MCP tools mirror CLI; `coord` aliases identical.
- Modality parity updated in `scripts/modality-parity.yml`; skill + reference docs updated.
- Works with `state.backend=local`; remote DocumentStore workspaces degrade gracefully (recover operates on session-root JSON stores as today).

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| RFC-0013 AOS façade | Operators/agents — crash recovery playbook |
| RFC-0007 ACL | Lease/worktree/claim mutations |
| RFC-0008 task graph | Stuck node requeue |
| RFC-0011 merge (optional) | Stale merge detection/cancel |
| RFC-0017 harness (optional) | Heartbeat policy alignment, run-scoped heartbeat |
| RFC-0021 scenario harness | Crash-recovery scenario fixtures |

## Suggested PR split

1. **Doctor enhancements** — recovery analyzer, `recovery_recipes[]`, `--agent-id` filter, docs report-only.
2. **Recover command** — `AosRecoverResult`, default safe bundle, explicit flags, task `requeue`, integration tests.
3. **Heartbeat + events** — `aos heartbeat`, `AosEventStore`, `WorkspaceEventService` wiring, skill/docs.

## Open questions

1. Should `doctor --fix` accept `--agent-id` to scope GC, or remain workspace-wide only?  
   **Recommendation:** v1 keep `--fix` workspace-wide (current behavior); agent scope lives on `recover`.
2. Should `recover` auto-call `heartbeat` before GC when active leases exist?  
   **Recommendation:** no — keep commands explicit; doctor recipe suggests heartbeat when leases near expiry.
3. Task `requeue` vs new status `failed` for stuck nodes?  
   **Recommendation:** `running → ready` for recoverability; use `block`/`cancel` only via explicit operator commands outside recover defaults.

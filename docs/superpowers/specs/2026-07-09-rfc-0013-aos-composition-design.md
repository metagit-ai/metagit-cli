# RFC-0013: Agent Operating System (AOS) — Composition Design

**Status:** Implemented  
**Date:** 2026-07-09  
**Series:** [ACL RFC series index](2026-07-09-acl-rfc-series-index.md)  
**Vision:** [agent-coordination.md](../../reference/agent-coordination.md) (RFC-0007 vision; original spec.md retired) § Long-Term Vision  
**Depends on:** RFC-0008–0012 foundations (compose what exists; degrade gracefully)  
**Plan:** [2026-07-09-rfc-0013-aos-composition.md](../plans/2026-07-09-rfc-0013-aos-composition.md)  
**Branch:** `feat/rfc-0013-aos`

## Summary

**Composition-only RFC.** Provide a unified operator/agent surface that answers “what is the coordination OS doing?” and “what should run next?” by aggregating ACL, task graph, context compile, semantic hints, merge queue, and scheduler — **without new core engines**. Metagit tracks intent across these subsystems; Git remains source of truth for code.

## Goals

- Façade module `metagit.core.aos` (thin) + CLI `metagit aos` with alias `metagit coord`.
- Commands: `status`, `doctor`, `next` (preview / commit / optional ACL hint apply).
- MCP `metagit_aos_*` with `metagit_coord_*` aliases returning the same JSON.
- Bundled skill `metagit-aos` documenting the control loop; short pointer from `metagit-agent-coordination`.
- Policy/observability: document event `source` values and recommended dashboards (events poll), not a new telemetry stack.
- Graceful degradation when 0009–0012 are not installed yet (show ACL + tasks only).

## Non-Goals

- New task/merge/schedule/semantic engines.
- New persistence backend (no `.metagit/aos/` snapshot cache in v1).
- Replacing MCP control-center or campaign systems.
- Multi-tenant hosted AOS product.
- Launching models or embedding agent runtimes.
- A full `aos run` control-loop executor (that would become an orchestrator engine).

## Architecture

Thin aggregator: collectors behind Protocol interfaces so tests stub absent RFCs and runtime degrades cleanly.

```text
metagit aos|coord  status|doctor|next
              │
              ▼
         AosService
    ┌─────┼─────┬─────┬─────┬─────┐
    ▼     ▼     ▼     ▼     ▼     ▼
  ACL   task  compile semantic merge schedule
  0007  0008  0009?   0010?   0011? 0012?
```

**Package:** `src/metagit/core/aos/`

| Concern | Behavior |
|---------|----------|
| `status` | Read-only snapshot; each subsystem section has `available: bool` + summary fields |
| `doctor` | Findings + suggested commands; optional `--fix` for safe ACL GC only |
| `next` | Composed “what to do now” envelope; preview by default |

Approach locked: **thin aggregator** (no snapshot cache, no `aos run` chain executor).

## Interfaces

### CLI

Primary group `aos`; alias group `coord` (identical commands/flags).

```bash
metagit aos status [--json]
metagit aos doctor [--json] [--fix] [--yes]
metagit aos next [--json] [--commit] [--apply-hints] [--agent-id …] [--graph-id …]

# aliases
metagit coord status|doctor|next …
```

### MCP

ACTIVE-gated. Alias tools share handlers with primary tools.

| Primary | Alias | Purpose |
|---------|-------|---------|
| `metagit_aos_status` | `metagit_coord_status` | Snapshot JSON |
| `metagit_aos_doctor` | `metagit_coord_doctor` | Findings; `fix` + `confirm` for safe GC |
| `metagit_aos_next` | `metagit_coord_next` | Preview envelope; `commit` / `apply_hints` |

### Snapshot / envelope shapes (v1)

**Status** — top-level `generated_at` plus `subsystems`:

- `acl` — lease/worktree/claim counts (always expected when 0007 present)
- `taskgraph` — ready/blocked/in-progress counts
- `context_compile` — available flag + last-compile hint if cheap to read (no forced compile)
- `semantic` — conflict count when 0010 present
- `merge` — queued/running/conflict counts when 0011 present
- `scheduler` — recent decision summary / policy weights when 0012 present

Each subsystem object includes at least `available: bool`. Missing imports or empty stores → `available: false` (or true with zero counts when the package exists but has no data — prefer package-present = available).

**Doctor** — status fields plus:

- `findings[]` — `{severity, code, message, subsystem}`
- `suggested_commands[]` — copy-paste CLI strings
- `fixed[]` — only when `--fix --yes` ran (what GC did)

**Next** — composed envelope:

- `decision?` — schedule decision payload or ready-node fallback summary
- `compile_command?` — suggested `metagit context compile …` string (not executed by AOS)
- `acl_commands[]` — suggested allocate/lease/worktree/claim strings
- `committed: bool` — whether a schedule decision was recorded
- `hints_applied: bool` — whether ACL bind APIs were invoked
- `scheduler_available: bool`

## Doctor behavior

- **Default:** report-only. Never mutate.
- **Findings (examples):** expired/stale leases, orphan worktrees, blocked tasks, missing optional subsystems, merge-queue pressure, empty ready set.
- **`--fix`:** requires **`--yes`** (MCP: `fix=true` and `confirm=true`). Without confirm → error, no mutation.
- **Allowed `--fix` actions (safe GC only):** expired lease cleanup and/or `worktree gc` via existing ACL services.
- **Never via doctor `--fix`:** claim release, merge cancel, task complete/block, schedule policy changes, git commits/pushes.

## `next` behavior

- **Default (preview):** score/ready peek **without** appending `.metagit/schedule/decisions.jsonl`. Implementation may add a thin `SchedulerService` preview/`dry_run` hook or reuse pure scoring — not a new engine.
- **`--commit`:** delegate to `SchedulerService.next()` so the decision is recorded and scheduler events emit as today.
- **`--apply-hints`:** execute ACL bind sequence for the chosen node using existing coordination APIs (allocate/lease/worktree/claim as already suggested by dispatch / `task bind-acl`). Requires `--agent-id` when applying. Never launches models. Never runs context compile (only returns `compile_command`).
- **Degrade path:** if scheduler unavailable, fall back to first ready task node from RFC-0008; if no ready nodes, return empty envelope with reasons. If taskgraph unavailable, `next` fails clearly (0008 is the minimum composition floor with 0007).

## Persistence

None new — read-only aggregation for status/preview. Mutations only through existing ACL (doctor `--fix`, `next --apply-hints`) or scheduler (`next --commit`) stores.

## Events

None required from AOS itself in v1. Subsystem events remain authoritative (`source=acl|taskgraph|…|scheduler`). Optional later: periodic `AosSnapshot` (out of v1).

## Skills & docs

- New bundled skill **`metagit-aos`**: composed control loop  
  `schedule/aos next → compile → ACL bind → work → complete → merge enqueue`.
- Short pointer section in **`metagit-agent-coordination`**.
- Public reference **`docs/reference/aos.md`** when the RFC ships (not before).
- Modality feature id: **`aos_status`** (aliases documented; not separate engines).

## Acceptance

- `aos status --json` works with only 0007+0008 present.
- Missing 0009–0012 sections show `available: false` without crashing.
- `coord` aliases behave identically to `aos`.
- Doctor without `--fix` never mutates; `--fix` without `--yes` errors; `--fix --yes` only ACL safe GC.
- `next` preview does not append schedule decisions; `--commit` does.
- `--apply-hints` never launches models and never mutates git beyond ACL APIs.
- Skill + docs + modality land; series index marks 0013 shipped when façade lands.
- No new modality engines beyond `aos_status`.

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| 0007–0012 (soft; 0007+0008 hard floor for useful status/next) | Operators/agents; closes ACL RFC series 0008–0013 |

## Decisions (locked)

1. **Naming:** CLI/MCP primary `aos`; alias `coord` / `metagit_coord_*`.
2. **Doctor:** report-only by default; `--fix --yes` for safe ACL GC only.
3. **Skills:** new `metagit-aos` + pointer from `metagit-agent-coordination`.
4. **Surface:** `status` + `doctor` + `next` (no `aos run` executor).
5. **`next` recording:** preview by default; `--commit` records via scheduler.
6. **`--apply-hints`:** ACL bind only; never launches models; compile is hint-only.
7. **Architecture:** thin aggregator; no AOS persistence; no snapshot cache in v1.
8. **Modality:** `aos_status` only.

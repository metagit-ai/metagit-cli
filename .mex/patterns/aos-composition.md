---
name: aos-composition
description: Implementing or operating RFC-0013 AOS composition façade (status/doctor/next).
triggers:
  - "aos"
  - "coord status"
  - "RFC-0013"
  - "AosService"
  - "metagit aos"
  - "aos_status"
edges:
  - target: "../context/conventions.md"
    condition: when writing or reviewing AOS code
  - target: "agent-scheduler.md"
    condition: when wiring preview_next / commit schedule decisions
  - target: "agent-coordination-acl.md"
    condition: when doctor --fix or next --apply-hints touches ACL
  - target: "task-graph-intent.md"
    condition: when falling back to ready nodes without scheduler
  - target: "acl-rfc-series.md"
    condition: when placing AOS in the 0008–0013 series
last_updated: 2026-07-10
---

# AOS composition

## Context

RFC-0013 lives under `src/metagit/core/aos/`. It is composition-only: no new
engines and no `.metagit/aos/` persistence. CLI primary group is `aos`; alias
`coord`. Modality id: `aos_status`.

## Steps

1. Aggregate via collectors behind Protocols; missing 0009–0012 → `available: false`.
2. `status` is read-only; `doctor` is report-only unless `--fix --yes` (safe ACL GC only).
3. `next` defaults to `SchedulerService.preview_next` (no `decisions.jsonl` append);
   `--commit` calls `next()`; `--apply-hints` runs ACL bind APIs only (needs `--agent-id`).
4. Expose thin CLI `metagit aos|coord` and ACTIVE-gated MCP `metagit_aos_*` /
   `metagit_coord_*` sharing `AosService`.
5. Keep skill `metagit-aos` + pointer from `metagit-agent-coordination`; register
   modality in `scripts/modality-parity.yml`.

## Gotchas

- Doctor `--fix` without `--yes` (MCP `confirm`) must error — never mutate.
- Allowed `--fix` actions: lease expire-on-list + `WorktreeService.gc()` only.
- `--apply-hints` never launches models and never runs context compile.
- Hard floor for useful status/next is RFC-0007 + RFC-0008.

## Verify

- `uv run pytest tests/core/aos tests/cli/commands/test_aos_cli.py tests/core/mcp/test_aos_tools.py -q`
- `task qa:prepush`

## Debug

- Empty `next` envelope → check taskgraph ready set / scheduler availability.
- Doctor findings stale after `--fix` → re-run `status` collectors (service refreshes after fix).

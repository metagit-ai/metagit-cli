# RFC-0013: Agent Operating System (AOS) — Composition Design

**Status:** Draft  
**Date:** 2026-07-09  
**Series:** [ACL RFC series index](2026-07-09-acl-rfc-series-index.md)  
**Vision:** [agent-coordination.md](../../reference/agent-coordination.md) (RFC-0007 vision; original spec.md retired) § Long-Term Vision  
**Depends on:** RFC-0008–0012 foundations (compose what exists; degrade gracefully)  
**Plan:** [2026-07-09-rfc-0013-aos-composition.md](../plans/2026-07-09-rfc-0013-aos-composition.md)

## Summary

**Composition-only RFC.** Provide a unified operator/agent surface that answers “what is the coordination OS doing?” by aggregating ACL, task graph, context compile, semantic hints, merge queue, and scheduler — **without new core engines**. Metagit tracks intent across these subsystems; Git remains source of truth for code.

## Goals

- Façade module `metagit.core.aos` (thin) + CLI `metagit aos status` (+ optional `aos doctor`).
- MCP `metagit_aos_status` returning a single JSON snapshot.
- Bundled skill `metagit-aos` (or extend control-center) documenting the control loop: schedule next → compile → ACL bind → work → complete → merge enqueue.
- Policy/observability: document event `source` values and recommended dashboards (events poll), not a new telemetry stack.
- Graceful degradation when 0009–0012 are not installed yet (show ACL + tasks only).

## Non-Goals

- New task/merge/schedule/semantic engines.
- New persistence backend.
- Replacing MCP control-center or campaign systems.
- Multi-tenant hosted AOS product.

## Architecture

```text
metagit aos status
        │
        ├── coordination (0007)
        ├── taskgraph (0008)
        ├── context compile summary (0009 if present)
        ├── semantic conflict count (0010 if present)
        ├── merge queue (0011 if present)
        └── schedule decision preview (0012 if present)
```

## Interfaces

### CLI

```bash
metagit aos status [--json]
metagit aos doctor [--json]   # optional: missing subsystems, stale leases, blocked tasks
```

### MCP

`metagit_aos_status`, optional `metagit_aos_doctor`

## Persistence

None new — read-only aggregation.

## Events

None required; may re-emit a periodic `AosSnapshot` later (out of v1).

## Acceptance

- `aos status --json` works with only 0007+0008 present.
- When 0011/0012 exist, sections appear without separate commands.
- Skill documents the composed loop; series index marks 0013 shipped when façade+docs land.
- No new modality engines beyond `aos_status` feature flags.

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| 0007–0012 (soft) | Operators/agents; future RFCs beyond this series |

## Open questions

1. Name collision: keep `aos` vs `coord status`?
2. Should doctor auto-run lease GC / worktree gc?

**Recommendation:** keep `aos` to match vision naming; doctor is report-only in v1 (print suggested commands).

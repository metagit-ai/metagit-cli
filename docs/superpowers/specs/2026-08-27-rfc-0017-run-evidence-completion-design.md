# RFC-0017 completion: Run Evidence & Ledger Read Surface — Design

**Status:** Accepted for implementation  
**Date:** 2026-08-27  
**Series:** [Agent reliability index](2026-08-27-agent-reliability-series-index.md) · builds on [RFC-0017 harness](2026-07-31-rfc-0017-agentic-workload-harness-design.md) + shipped `metagit.core.routing`  
**Plan:** implement in-tree on `feat/agent-reliability-series` (this doc is the locked design)

## Summary

Extend the existing routing run ledger so agents get durable, queryable evidence of control-loop steps. Keep local YAML one-file-per-run as default; DocumentStore `harness.runs` remains deferred.

## Goals

1. Enrich `RunEvidence` with ordered `steps[]`, optional intent / token / cost fields.
2. CLI `metagit run show|replay|export` (+ existing open/close/list).
3. MCP `metagit_run_show` / `metagit_run_replay` / `metagit_run_list`.
4. On `aos next --commit`, when routing is configured, open (or ensure) a run and record an `aos_next` step; surface `run_id` on `AosNextResult`.
5. Append-only step API; redaction helper for export/show.
6. Concurrent writers do not corrupt the ledger (file lock + unique run ids).

## Non-Goals

- Remote DocumentStore backend (follow-on).
- Replacing request-class catalog semantics.
- Launching models from AOS.

## Decisions (locked)

| # | Decision |
|---|----------|
| D1 | Storage remains `RoutingConfig.runs` YAML files. |
| D2 | System class `REQ-AOS-NEXT` auto-ensured when AOS records a committed next. |
| D3 | `replay --dry-run` returns reconstructed steps JSON; no mutations. |
| D4 | Run ids include a short uniqueness suffix to avoid second-resolution collisions. |

## Acceptance

- `metagit run show|replay|export` work with `--json`.
- Concurrent open_run from multiple threads succeeds without StateConflictError storms.
- Modality `run_ledger` + `docs/reference/run-ledger.md`.
- `aos next --commit --json` includes `run_id` when routing configured.

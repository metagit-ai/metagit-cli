# RFC-0012 Distributed Agent Scheduler — Implementation Plan

> **For agentic workers:** Expand into bite-sized TDD steps when the RFC-0012 MR starts.

**Goal:** Score ready task nodes and return the next schedule decision + dispatch hints without launching models or mutating git.

**Architecture:** `src/metagit/core/scheduler/` reads taskgraph ready set + local `policy.json`, scores nodes (priority, affinity, simple cost), optionally soft-checks merge queue depth, appends decisions JSONL, exposes CLI/MCP.

**Tech Stack:** Pydantic, Click, MCP, pytest.

**Design:** [2026-07-09-rfc-0012-agent-scheduler-design.md](../specs/2026-07-09-rfc-0012-agent-scheduler-design.md)

## Out of scope

Multi-host/GPU brokers, embedding agent runtimes, guaranteed optimal scheduling, AOS façade (0013), SPA.

## File map

| Action | Path |
|--------|------|
| Create | `src/metagit/core/scheduler/{__init__,models,paths,store,service,scoring}.py` |
| Create | `src/metagit/cli/commands/schedule.py` |
| Create | `tests/core/scheduler/` |
| Create | `docs/reference/agent-scheduler.md` |
| Modify | optional dispatch-plan enrichment; MCP; modality-parity; CHANGELOG; ROUTER; series index |

## Phases

- [ ] **Phase 0 — Policy model:** weights for priority, affinity, cost; defaults; load/save `.metagit/schedule/policy.json`.
- [ ] **Phase 1 — Scoring:** deterministic score from ready nodes; unit tests for tie-break rules.
- [ ] **Phase 2 — `schedule next`:** return decision payload with reasons + optional acl/compile command hints.
- [ ] **Phase 3 — Soft merge backpressure:** if merge queue present and over threshold, prefer non-conflicting repos or skip with reason.
- [ ] **Phase 4 — CLI/MCP/status/docs/QA.**

## Acceptance checklist

- [ ] Higher priority wins deterministically.
- [ ] Scheduler performs no git mutations.
- [ ] Works with taskgraph only (0011 optional).
- [ ] Parity + docs updated.

## Expand-at-MR-start

Lock tie-break algorithm in tests before wiring CLI.

# RFC-0013 Agent Operating System (Composition) — Implementation Plan

> **For agentic workers:** Expand into bite-sized steps when the RFC-0013 MR starts. This RFC must not grow new engines.

**Goal:** Ship a thin composition façade (`metagit aos status` / doctor + MCP + skill) that aggregates ACL, task graph, and any present 0009–0012 subsystems into one operator snapshot.

**Architecture:** `src/metagit/core/aos/status.py` imports/calls existing services behind try/feature detection; no new persistence; CLI + MCP only.

**Tech Stack:** Pydantic response model, Click, MCP, pytest with fakes/stubs for missing subsystems.

**Design:** [2026-07-09-rfc-0013-aos-composition-design.md](../specs/2026-07-09-rfc-0013-aos-composition-design.md)

## Out of scope

New task/merge/schedule/semantic engines, new DB, auto GC mutations, SPA, replacing control-center.

## File map

| Action | Path |
|--------|------|
| Create | `src/metagit/core/aos/{__init__,models,status.py}` |
| Create | `src/metagit/cli/commands/aos.py` |
| Create | `tests/core/aos/test_status.py` |
| Create | `skills/metagit-aos/SKILL.md` (+ packaged copy) **or** extend `metagit-control-center` / `metagit-agent-coordination` |
| Create | `docs/reference/aos.md` |
| Modify | MCP, modality-parity (`aos_status`), CHANGELOG, ROUTER, series index |

## Phases

- [ ] **Phase 0 — Snapshot model:** sections with `available: bool` per subsystem.
- [ ] **Phase 1 — Collectors:** ACL counts, task ready/blocked, optional compile/semantic/merge/schedule fields.
- [ ] **Phase 2 — CLI/MCP:** `aos status --json`, `aos doctor --json` (report-only suggested commands).
- [ ] **Phase 3 — Skill + docs:** composed control loop; link series index.
- [ ] **Phase 4 — QA + mark series complete** in index/ROUTER.

## Acceptance checklist

- [ ] Status works with only 0007+0008.
- [ ] Missing subsystems show `available: false` without crashing.
- [ ] Doctor does not mutate state.
- [ ] `task qa:prepush` green.

## Expand-at-MR-start

Implement collectors behind Protocol interfaces so tests stub absent RFCs cleanly.

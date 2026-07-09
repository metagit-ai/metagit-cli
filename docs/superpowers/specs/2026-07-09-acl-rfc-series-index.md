# ACL RFC Series Index (0007–0013)

**Status:** Living index  
**Date:** 2026-07-09  
**Vision source:** [agent-coordination.md](../../reference/agent-coordination.md) (RFC-0007; original root `spec.md` retired)  
**Shipped reference:** [docs/reference/agent-coordination.md](../../reference/agent-coordination.md)

This index tracks the buildable RFC series that evolves Metagit from a multi-repo catalog into an agent coordination / operating layer. Each RFC has a **design spec** and an **implementation plan** under `docs/superpowers/`.

## Shared locks (all RFCs)

- **Depends on RFC-0007 ACL** — `metagit.core.coordination`, CLI `branch|lease|worktree|claim`, MCP tools, persistence under session/manifest root `.metagit/{branches,leases,worktrees,claims,agents,events}/`, configurable `workspace.worktrees_path` (default `.worktrees`).
- **Modality default:** CLI + MCP + core services + docs/skills. No SPA. Thin `/v3/ops` only when remote-state sharing is required.
- **Persistence default:** local JSON under session/manifest root. No SQLite/Postgres migration in 0008–0013 unless a specific RFC explicitly opens that door (default: closed).
- **Lease naming:** ACL branch leases ≠ handoff claim TTL (`metagit context handoff claim --ttl`).
- **Git authority:** advisory claims / semantic ownership never replace Git as source of truth for code.
- **Public docs:** do not add `docs/reference/rfc-000N*` stubs until that RFC ships; keep build docs here.

## Dependency graph

```text
RFC-0007 ACL (shipped)
  └─► RFC-0008 Task Graph & Intent Engine
        ├─► RFC-0009 Agent Context Compiler
        ├─► RFC-0011 Merge Orchestrator & Conflict Resolution
        │     └─► RFC-0012 Distributed Agent Scheduler
        └─► RFC-0010 Semantic Repository Knowledge Graph
              (may parallel 0009 after 0008 models exist; feeds claim advice)
RFC-0013 Agent Operating System (composition only)
  (after 0008–0012 foundations exist enough to compose; no new engines)
```

## Status table

| RFC | Title | Design | Plan | Depth | Status |
|-----|-------|--------|------|-------|--------|
| 0007 | Agent Coordination Layer (foundation) | [agent-coordination.md](../../reference/agent-coordination.md) | Historical Cursor plan `rfc-0007_acl_foundation_*.plan.md` (local) | executed | **Shipped** |
| 0008 | Task Graph & Intent Engine | [design](2026-07-09-rfc-0008-task-graph-intent-design.md) | [plan](../plans/2026-07-09-rfc-0008-task-graph-intent.md) | fuller | **Implemented** (branch `feat/rfc-0008-task-graph`) |
| 0009 | Agent Context Compiler | [design](2026-07-09-rfc-0009-context-compiler-design.md) | [plan](../plans/2026-07-09-rfc-0009-context-compiler.md) | phased | **Implemented** (same branch) |
| 0010 | Semantic Repository Knowledge Graph | [design](2026-07-09-rfc-0010-semantic-kg-design.md) | [plan](../plans/2026-07-09-rfc-0010-semantic-kg.md) | fuller (TDD) | **Implemented** (in progress on `feat/rfc-0010-0011`; Task 9 GitNexus import deferred) |
| 0011 | Merge Orchestrator & Conflict Resolution | [design](2026-07-09-rfc-0011-merge-orchestrator-design.md) | [plan](../plans/2026-07-09-rfc-0011-merge-orchestrator.md) | fuller (TDD) | **In progress** (`feat/rfc-0010-0011`) |
| 0012 | Distributed Agent Scheduler | [design](2026-07-09-rfc-0012-agent-scheduler-design.md) | [plan](../plans/2026-07-09-rfc-0012-agent-scheduler.md) | phased | Draft |
| 0013 | Agent Operating System (composition) | [design](2026-07-09-rfc-0013-aos-composition-design.md) | [plan](../plans/2026-07-09-rfc-0013-aos-composition.md) | phased | Draft |

## Next MR

**RFC-0010 + RFC-0011** on branch `feat/rfc-0010-0011` (worktree `.worktrees/rfc-0010-0011`). RFC-0010 is implemented except the optional Task 9 GitNexus import, which is deferred. Do not start RFC-0011 implementation until its plan is explicitly opened.

## Document conventions

Each **design** includes: Summary, Goals, Non-Goals, Architecture, Interfaces, Persistence, Events, Acceptance, Dependencies, Open questions (or locked Decisions).

Each **plan** includes: Goal, Architecture, Tech stack, Out of scope, file map, ordered phases/tasks with checkboxes. RFC-0008 and RFC-0010 include bite-sized TDD steps.

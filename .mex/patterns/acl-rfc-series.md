---
name: acl-rfc-series
description: Navigate or extend the RFC-0007–0013 agent coordination series (designs and implementation plans).
edges:
  - target: agent-coordination-acl.md
    condition: when implementing shipped ACL primitives
  - target: aos-composition.md
    condition: when working on the RFC-0013 composition façade
  - target: agent-scheduler.md
    condition: when working on RFC-0012 scheduling
  - target: ../context/architecture.md
    condition: when placing new packages under src/metagit/core
last_updated: 2026-07-10
---

# ACL RFC series (0008–0013)

## When to use

Navigating the coordination series, merging remaining MRs, or starting
follow-on work **beyond** 0013 (new engines need a new RFC — not 0013).

## Status (as of RFC-0013)

| RFC | Role | Pattern |
|-----|------|---------|
| 0007 | ACL foundation (shipped) | `agent-coordination-acl.md` |
| 0008 | Task graph | `task-graph-intent.md` |
| 0009 | Context compiler | (see series index / context docs) |
| 0010 | Semantic KG | `semantic-graph-service.md` |
| 0011 | Merge orchestrator | `merge-orchestrator.md` / `merge-orchestrator-store.md` |
| 0012 | Scheduler | `agent-scheduler.md` |
| 0013 | AOS composition (no new engines) | `aos-composition.md` |

## Do

1. Read the series index first: `docs/superpowers/specs/2026-07-09-acl-rfc-series-index.md`.
2. Implement only the RFC for the current MR; keep shared locks (modality, local JSON, lease naming).
3. Prefer fuller TDD plans (0008/0010 style) for new engines; 0013 must stay composition-only.
4. After shipping a series RFC, update this pattern + `ROUTER.md` project state.

## Don't

- Don't add new engines under RFC-0013 — open a new RFC instead.
- Don't add public `docs/reference/rfc-000N` stubs until that RFC ships.
- Don't introduce SQLite/Postgres unless a specific RFC explicitly opens it.
- Don't treat AOS as a model launcher or control-loop executor (`aos run`).

## Verify

```bash
ls docs/superpowers/specs/2026-07-09-rfc-000*.md docs/superpowers/specs/2026-07-09-rfc-001*.md
ls docs/superpowers/plans/2026-07-09-rfc-000*.md docs/superpowers/plans/2026-07-09-rfc-001*.md
test -f .mex/patterns/aos-composition.md
```

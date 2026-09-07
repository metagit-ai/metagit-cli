# RFC-0030: Component Ownership / Claims — Design

**Status:** Implemented
**Date:** 2026-09-06
**Series:** [Component Context Graph index](2026-09-06-rfc-0026-component-context-graph-index.md)
**Depends on:** [RFC-0026](2026-09-06-rfc-0026-component-model-design.md), [RFC-0027](2026-09-06-rfc-0027-component-resolution-design.md)
**Plan:** [2026-09-06-rfc-0028-0032-remaining-series.md](../plans/2026-09-06-rfc-0028-0032-remaining-series.md)

## Summary

Let agents claim a catalogued component without claiming the whole repository. Component claims are **advisory semantic ownership**, not git isolation. Existing repository + glob claims keep working.

## Goals

- Optional `component` on `FileClaim`.
- Default claim patterns to the component path when patterns are omitted.
- CLI / MCP `--component` on declare and check.
- Overlap detection still keyed by `repository` (`project/repo`) + patterns.

## Non-Goals

- Automatic worktree / branch allocation per component
- Rewriting `ConceptOwnership.repository` to a three-segment id (keep `project/repo` + globs)
- Task assignment scheduler changes
- SPA claims UI

## Decisions (locked)

1. **`FileClaim.component: str | None = None`** stores the component **name** (not the three-segment id). `repository` stays `project/repo`.
2. **Declare** with `--component` requires `repository` to be `project/repo`. Resolve via `ComponentResolver.get`. Unknown component → error.
3. **Empty patterns + component** → `[f"{path}/**"]` except path `.` → `["**"]`.
4. **Explicit patterns + component** are stored as given; do not rewrite.
5. **Check** with `--component` uses the same default-pattern expansion when patterns are empty, then existing overlap logic.
6. **Two agents** on `web` vs `api` in the same repo do not conflict when their expanded patterns do not overlap.
7. **Same component** (or overlapping globs) still conflict under `--strict`.
8. **Semantic graph** stays pattern-based. `claim check` continues to attach `concept_hints` via existing `advise_claim_patterns`.
9. **MCP** `metagit_claim_declare` / `metagit_claim_check` gain optional `component`.
10. **Modality:** extend existing claim/ACL docs; new id `component_claim` only if a distinct operator surface is documented in `docs/concepts/components.md`.

## Tests

- Declare `--component web` with no patterns stores `apps/web/**`.
- Web vs api in one repo: check is clean.
- Two declares on `web` overlap.
- Unknown component errors.
- Claims without `--component` unchanged.

# RFC-0032: Derived Working Sets from Components — Design

**Status:** Implemented
**Date:** 2026-09-06
**Series:** [Component Context Graph index](2026-09-06-rfc-0026-component-context-graph-index.md)
**Depends on:** [RFC-0028](2026-09-06-rfc-0028-component-graph-design.md), [RFC-0029](2026-09-06-rfc-0029-component-compile-design.md)
**Plan:** [2026-09-06-rfc-0028-0032-remaining-series.md](../plans/2026-09-06-rfc-0028-0032-remaining-series.md)

## Summary

Extend existing `metagit project derived create|include` so a selection may be `project/repo/component`. The derived repo copy carries only the selected component(s), optionally plus graph neighbors. Do **not** add `metagit context derive`.

## Goals

- Selection grammar: `project/repo` (unchanged) or `project/repo/component`.
- Copy `components` onto derived repos (today identity copy omits them).
- Optional `--include-dependencies` using RFC-0028 neighborhood depth 1 outbound `depends_on`.

## Non-Goals

- New CLI group `context derive`
- Physical sparse checkout / copying files into `working-set/`
- Cross-manifest derived projects

## Decisions (locked)

1. **`parse_selection`** returns `tuple[str, str]` today. Change to a small result type:
   - `project: str`
   - `repo: str`
   - `component: str | None`
   Two-segment stays repo-wide; three-segment is component-scoped. Other segment counts remain `CatalogError`.
2. **`DerivedSourceScope`** gains `components: list[str] = []`. Empty means “whole source repo” (current behavior). Non-empty is the allow-list of component names from that source repo.
3. **Create/include `project/repo`:** copy identity fields **and** full `components` list from source (fix the current omission).
4. **Create/include `project/repo/component`:** copy identity fields; set `components` to that one `Component` (deep copy). Append name to `DerivedSourceScope.components`.
5. **`--include-dependencies`** (create only, default off): for each component selection, add neighborhood nodes at depth 1 direction `out` type filter `depends_on`. Same-repo neighbors merge into that derived repo’s `components[]`. Cross-repo neighbors add extra derived repo entries (same as extra `--from` selections) with only those components.
6. **Refresh** recopies component specs from source for names listed in `DerivedSourceScope.components`, or all components if that list is empty.
7. **Exclude** still removes a derived **repo**. To drop one component, include is not inverted — document `refresh` after manual YAML edit; do not add `derived exclude --component` in this slice.
8. **MCP** `metagit_project_derived_create` / `include` accept the same `project/repo/component` strings. Add optional `include_dependencies` bool on create.
9. **Modality:** extend `derived_projects` markers.

## Tests

- `--from platform/core` copies both `web` and `api` components.
- `--from platform/core/web` copies only `web`.
- `--from platform/core/web --include-dependencies` also copies `api`.
- Two-segment selections still work.
- Invalid `a/b/c/d` is an error.

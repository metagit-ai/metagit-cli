---
name: derived-projects-skills-surface
description: Create surgical derived workspace projects and inventory layered skills for agents.
last_updated: 2026-09-06
---

# Pattern: Derived projects + skills surface

## When

An agent needs a named subset of umbrella repos to sync and work on, and/or needs to see which skills apply at workspace vs project vs repo scope.

## Steps

1. Discover repos: `metagit context pack --tier 1 --json` / `metagit search`.
2. Create derived project: `metagit project derived create -n <name> --from P/R … --json` (or `P/R/C`; `--include-dependencies` adds outbound `depends_on` neighbors).
3. Sync: `metagit project -p <name> sync`.
4. Inventory skills: `metagit skills surface -p <name> --json`.
5. Refresh identity when sources change: `metagit project -p <name> derived refresh`.
6. Change membership only via `include` / `exclude` (never assume live queries). Exclude removes a repo; drop one component by editing YAML then refresh.

## Gotchas

- Without dedupe (create `--no-dedupe`), duplicate URL/path identities fail.
- Refresh errors if the source project/repo was removed; membership is not auto-dropped.
- `parse_selection` is two or three `/` segments only (`project/repo` or `project/repo/component`). Four segments are `CatalogError`.
- Repo-wide create copies full `components[]`. Three-segment copies that one component and sets `DerivedSourceScope.components`.
- Include of another component on an existing derived repo merges into `repos[].components` and `derived.sources[].components` (not a silent `noop`). Two-segment include on an existing repo widens to the full source list (empty allow-list).
- Skills suggest → `agent_profile` is phase 2; do not vendor CC BY-NC skill registries.
- Do not add `metagit context derive`.

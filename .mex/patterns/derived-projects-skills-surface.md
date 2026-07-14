---
name: derived-projects-skills-surface
description: Create surgical derived workspace projects and inventory layered skills for agents.
last_updated: 2026-07-14
---

# Pattern: Derived projects + skills surface

## When

An agent needs a named subset of umbrella repos to sync and work on, and/or needs to see which skills apply at workspace vs project vs repo scope.

## Steps

1. Discover repos: `metagit context pack --tier 1 --json` / `metagit search`.
2. Create derived project: `metagit project derived create -n <name> --from P/R … --json`.
3. Sync: `metagit project -p <name> sync`.
4. Inventory skills: `metagit skills surface -p <name> --json`.
5. Refresh identity when sources change: `metagit project -p <name> derived refresh`.
6. Change membership only via `include` / `exclude` (never assume live queries).

## Gotchas

- Without dedupe (create `--no-dedupe`), duplicate URL/path identities fail.
- Refresh errors if the source project/repo was removed; membership is not auto-dropped.
- Skills suggest → `agent_profile` is phase 2; do not vendor CC BY-NC skill registries.

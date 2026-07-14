# Derived Projects + Skills Inventory Design

**Date:** 2026-07-14  
**Status:** Implemented (phase 1)

## Summary

First-class **derived workspace projects** live in the same umbrella `.metagit.yml`. Membership is frozen at create; identity fields refresh from `derived_from` sources. Separate sync mounts reuse existing `ProjectManager.sync` and prefer per-project dedupe. **Skills surface** inventories on-disk vendor skills plus declared `agent_profile.skills` across workspace/project/repo.

## Decisions

- Checkout model: derived projects (not git subtrees, not virtual-only views)
- Placement: same umbrella manifest
- Provenance: hybrid (frozen membership; refreshable identity)
- Skills v1: inventory only; autoskills-style suggest deferred (CC BY-NC — inspiration only)

## Non-goals (this slice)

- Git subtree / sparse-checkout working repos
- Child/sibling `.metagit.yml` federation
- Live membership queries that auto-mutate `repos[]`
- Autoskills install pipeline / registry vendoring

## Phase 2 note

Suggest stack-matched skill ids into the appropriate `agent_profile` scope (workspace vs project vs repo), approval-gated, without depending on a non-commercial third-party registry.

## Surfaces

- CLI: `metagit project derived create|refresh|include|exclude`, `metagit skills surface`
- MCP: `metagit_project_derived_*`, `metagit_skills_surface`
- Docs: `docs/reference/derived-projects.md`, `docs/reference/skills-surface.md`
- Example: `examples/derived-workspace/.metagit.yml`

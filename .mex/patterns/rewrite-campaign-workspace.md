---
name: rewrite-campaign-workspace
description: Bootstrap a reference-implementation rewrite workspace (source + target repos, campaign, parity registry).
triggers:
  - "language rewrite"
  - "reference implementation migration"
  - "metagit-rewrite"
edges:
  - target: patterns/cli-tui-hub.md
    condition: when extending TUI or CLI flows for rewrite workspaces
  - target: patterns/bootstrap-metagit-config.md
    condition: when creating or validating rewrite coordinator manifests
last_updated: 2026-07-07
---

# Reference rewrite workspace

## Context

Use when one repo is the **spec** and a sibling repo is the **rewrite** (new language/stack).
Metagit tracks repo-level rollups via campaigns and module-level parity via `_rewrite/parity-registry.yml`.

Guide: `docs/metagit-rewrite-workspace.md` · Skill: `metagit-rewrite-campaign` · Example: `examples/metagit-rewrite/`

## Steps

1. `metagit init --template metagit-rewrite` or copy `examples/metagit-rewrite/.metagit.yml`.
2. Adjust source/target URLs; run `metagit config validate` and `metagit project sync --project rewrite`.
3. Ensure `_campaigns/<slug>.yml` exists (init template writes one; or `metagit campaign new … --reference rewrite/source`).
4. Copy `parity-registry.example.yml` → `_rewrite/parity-registry.yml` and fill module paths.
5. Install skill: `metagit skills install --skill metagit-rewrite-campaign`.
6. Orchestrator loop: tier-2 pack → campaign status → objective upsert → subagent handoff → MR binding.

## Gotchas

- Parity registry is a **BYO convention** — not validated by metagit schema.
- Source repo is read-only for rewrite agents unless fixing reference blockers.
- `reference_impl` on the campaign must match the source repo path (`rewrite/source`).
- Repomix profiles: `rewrite-source`, `rewrite-target` in `context_profiles.yaml`.
- Commit `_campaigns/` and `_rewrite/` for reviewable rollups.

## Verify

- [ ] `metagit config validate -c .metagit.yml`
- [ ] `metagit campaign validate`
- [ ] Example fixture passes in `scripts/manifest-fixtures.yml`
- [ ] `metagit init --list-templates` includes `metagit-rewrite`

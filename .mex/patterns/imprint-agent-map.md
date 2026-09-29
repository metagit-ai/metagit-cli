---
name: imprint-agent-map
description: Design for parent-project imprints, the committed agent map, and web sync failure detail. Load before implementing any of the three slices.
triggers:
  - imprint
  - agent-map
  - agent map sync
  - sync failure dialog
edges:
  - target: ../docs/superpowers/specs/2026-09-28-imprint-agent-map-sync-failures-design.md
    condition: when implementing or revising imprint, agent map, or sync failure detail
  - target: context/architecture.md
    condition: when wiring the resolver into the workspace index
last_updated: 2026-09-28
---

# Imprint, agent map, and sync failures

## Context

Design: `docs/superpowers/specs/2026-09-28-imprint-agent-map-sync-failures-design.md`.

Ship order is fixed: sync failure detail, then `agent-map/` plus the `AGENTS.md` fence, then imprint. Slice 2 reads literal `repos[]`. Slice 3 switches agent map sync onto `ImprintResolver`.

## Steps

1. Read the spec slice you are implementing. Leave the later slices alone.
2. Put business logic in `src/metagit/core/`. Keep CLI handlers thin.
3. For imprint, resolve a copy for the workspace index. Do not merge child repos inside `MetagitConfigManager.load_config` or `save`.
4. Register `agent_map` and `project_imprint` in `scripts/modality-parity.yml` when those slices land. Slice 1 extends the existing web sync surface.

## Gotchas

- `WorkspaceSyncService.sync_many` sets `ok` false when any row fails and omits a top-level `error`. The job must persist `results` or the dialog can only say "sync failed".
- Default `workspace.path` is `./.metagit`. `imprints` must be reserved or a project of that name syncs onto the cache directory.
- `.metagit/` is gitignored. The portable catalog for a model without the CLI is committed `agent-map/`, not the imprint cache.
- A parent `repos[]` entry with the same name replaces the child repo. `overrides.yml` may change tags and description only.

## Verify

- [ ] Failed sync job JSON includes `results` for each failed repo, and the dialog shows `project/repo` plus `error`.
- [ ] `agent map sync` rewrites the fenced `AGENTS.md` region once.
- [ ] Saving the parent manifest after a resolve does not expand imprinted repos into `.metagit.yml`.
- [ ] `task qa:prepush` passes, then `task gitnexus:analyze`.

## Debug

- Dialog still shows only "sync failed": `SyncJobStore.fail` was called without `results`.
- Search misses child repos: index build is still using `load_config` output instead of `ImprintResolver.effective_config`.
- Agent map empty after pull on a new machine: cache missing and no committed `agent-map/<project>.txt` yet. Run pull where the source is reachable, then commit `agent-map/`.

## Update Scaffold

- [ ] Update `.mex/ROUTER.md` when a slice ships
- [ ] Add reference docs listed in the spec when the slice ships

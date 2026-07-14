---
name: atlas-local
description: Operate or extend the repository-local Atlas semantic layer.
triggers:
  - "atlas"
  - "repository-local semantic layer"
edges:
  - target: modality-feature-registry.md
    condition: when changing the Atlas CLI or documentation surfaces
last_updated: 2026-07-14
---

# Local Atlas

## Steps

1. Keep canonical curated metadata under `.atlas/` separate from generated
   evidence and the rebuildable `.atlas/index/` cache.
2. Run `metagit atlas init|generate|validate|status|query|refresh` against the
   target repository with `--path` when it is not the current directory.
3. When changing the user-facing CLI, keep `atlas_local` markers and
   `docs/reference/atlas.md` synchronized.
4. Runtime JSON Schemas for `atlas validate` live under
   `src/metagit/data/schemas/atlas/` (packaged via `package-data`). Keep the
   docs/IDE copies in `schemas/atlas/` byte-identical; tests enforce parity.

## Verify

- `task qa:prepush` passes, including modality parity.
- `task gitnexus:analyze` completes after QA.

## Update Scaffold

- [ ] Update `.mex/ROUTER.md` if Atlas delivery status changes.
- [ ] Update this runbook when Atlas gains a recurring operational gotcha.

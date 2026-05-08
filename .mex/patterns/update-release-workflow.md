---
name: update-release-workflow
description: Safely replace or adjust GitHub release automation when post-merge release runs fail.
triggers:
  - "release workflow failing after merge"
  - "replace release automation"
  - "github actions release pipeline"
edges:
  - target: "context/conventions.md"
    condition: "before final verification to ensure required checks are run"
  - target: "ROUTER.md"
    condition: "after completing workflow changes to keep project state current"
last_updated: 2026-05-08
---

# Update Release Workflow

## Context
- Identify the active release workflows under `.github/workflows/`.
- Locate known-good reference workflows (for example `.github/example/`).
- Confirm expected release trigger model: `main` push for tag generation, tag push for publishing.

## Steps
1. Compare current release workflow files against the known-good copies.
2. Replace release orchestration logic first (for example `release-please` to semantic-tag flow).
3. Ensure publish workflow gates package publishing on tag refs only.
4. Ensure artifact lifecycle is intact (`build` -> `publish-test` -> `publish-prod` -> GitHub release).
5. Remove deprecated/conflicting workflows so only one release orchestration path is active.
6. Update `.mex/ROUTER.md` project state to match the new release mechanism.

## Gotchas
- Do not leave both `release-please` and semantic-tag workflows enabled unless intentionally dual-tracked.
- Keep token usage consistent with repo secrets (`PAT_TOKEN` vs `GITHUB_TOKEN`) and branch protection.
- Align tag format expectations between semantic tag creator and publish workflow filters.

## Verify
- Confirm all edited workflow YAML files parse in GitHub Actions syntax.
- Confirm semantic release workflow triggers on `push` to `main`.
- Confirm publish workflow only publishes when `github.ref` is a tag.
- Confirm no obsolete release workflow file remains active.

## Debug
- If release automation fails immediately on merge, inspect missing secret or permissions scope first.
- If publish never runs, inspect tag format mismatch versus `startsWith(github.ref, 'refs/tags/...')`.
- If GitHub release creation fails, confirm release job has `contents: write`.

## Update Scaffold
- [x] Update `.mex/ROUTER.md` "Current Project State" if release behavior changed
- [x] Update relevant `.mex/patterns/*` for this task type
- [x] Add this pattern to `.mex/patterns/INDEX.md`

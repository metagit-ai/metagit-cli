---
name: changelog-release
description: Maintain CHANGELOG.md, publish it on the docs site, and keep GitHub Releases aligned.
triggers:
  - "update changelog"
  - "release notes"
  - "docs changelog"
edges:
  - target: update-release-workflow.md
    condition: when changing semantic-release automation
last_updated: 2026-09-06
---

# Changelog and Release Notes

## Context

- Canonical file: root `CHANGELOG.md` (`## Unreleased` during development).
- Docs site mirrors it via `scripts/sync_docs_changelog.py` → `docs/changelog.md` (committed; semantic-release promotes both).
- GitHub Releases use the promoted changelog section, not raw `git log`.

## Steps

1. Add user-facing bullets under `## Unreleased` in `CHANGELOG.md`.
2. Run `task qa:prepush` — `changelog_check` fails if `src/`, `schemas/`, or `web/` changed without `CHANGELOG.md`.
3. On merge to `main`, semantic-release promotes `Unreleased`, commits `CHANGELOG.md`, tags, and publishes release notes.

## Gotchas

- `SKIP_CHANGELOG_CHECK=1` bypasses the gate locally only; CI always enforces it.
- Empty `Unreleased` falls back to grouped conventional commits at release time.
- Do not use Copilot/LLM steps for release notes — deterministic scripts avoid AI credit spend and drift.
- Tag/main Test runs lychee on `docs/**/*.md`. `_docs_site_changelog` must rewrite repo-root paths (`examples/`, `scripts/`, …) to GitHub URLs. Relative `examples/foo` in `docs/changelog.md` resolves as `docs/examples/foo` and fails (0.30.0 tag Test).

## Verify

- [ ] `uv run python scripts/validate_changelog.py` passes after product edits.
- [ ] `uv run python scripts/sync_docs_changelog.py && mkdocs build --strict` includes Changelog nav.
- [ ] `uv run python scripts/release_changelog.py --version X.Y.Z --dry-run` prints expected body.

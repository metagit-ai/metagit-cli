# Metagit Development Guide

Upon making changes run the following to validate everything before submitting a PR

```bash
task format lint:fix test
```

## MCP Development Notes

- Use `metagit mcp serve` to start the MCP stdio runtime.
- Use `--root <path>` to test workspace gating against a specific folder.
- Use `--status-once` for quick diagnostics without starting the message loop.
- MCP gating states:
  - `inactive_missing_config` when `.metagit.yml` is not present
  - `inactive_invalid_config` when `.metagit.yml` fails validation
  - `active` when `.metagit.yml` loads successfully

## Provider Source Sync

Use source sync to discover repositories from GitHub/GitLab and plan/apply workspace updates:

- Discover-only: `metagit project source sync --provider github --org <org> --mode discover`
- Additive apply: `metagit project source sync --provider github --org <org> --mode additive --apply`
- Reconcile apply: `metagit project source sync --provider gitlab --group <group> --mode reconcile --apply --yes`

## Changelog and releases

- Maintain user-facing changes under `## Unreleased` in root `CHANGELOG.md`.
- `task qa:prepush` and CI run `scripts/validate_changelog.py` when `src/`, `schemas/`, or `web/` change. Set `SKIP_CHANGELOG_CHECK=1` to bypass locally.
- The docs site publishes the same file at `/changelog/` — `task docs` and the docs workflow sync `CHANGELOG.md` into `docs/changelog.md` before `mkdocs build`.

## Semantic Release Tags

`.github/workflows/semantic-release.yaml` runs on merges to `main` and uses conventional commit prefixes to compute the next version.

- Promotes `## Unreleased` into a dated version section in `CHANGELOG.md`, commits to `main`, then tags.
- GitHub Release notes use the promoted changelog body (commit-log fallback only when `Unreleased` is empty).
- Release automation is deterministic (no LLM). GitHub Copilot AI credits are not a free pipeline for custom workflows; they meter Copilot Chat/agents/review features instead.

- `fix:` -> patch release (`X.Y.Z+1`) **default for most updates**
- `feat:` -> minor release (`X.Y+1.0`)
- `type(scope)!:` or `BREAKING CHANGE:` -> major release (`X+1.0.0`)

### Commit Prefix Guidance

Use patch semantics first (`fix:`) unless schema/config compatibility is intentionally broken.

- Use `fix:` for normal maintenance and safe behavior changes.
- Use `feat:` only for additive, backward-compatible functionality.
- Use `!` / `BREAKING CHANGE` when changing `.metagit.yml` or app config schema in a non-backward-compatible way.

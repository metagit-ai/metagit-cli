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

## Semantic Release Tags

`release-please` runs on merges to `main` and uses conventional commit prefixes to prepare/version releases.

- It opens/updates a release PR with computed next version + changelog.
- When that PR is merged, it creates the semantic tag (`vX.Y.Z`) and GitHub release.

- `fix:` -> patch release (`X.Y.Z+1`) **default for most updates**
- `feat:` -> minor release (`X.Y+1.0`)
- `type(scope)!:` or `BREAKING CHANGE:` -> major release (`X+1.0.0`)

### Commit Prefix Guidance

Use patch semantics first (`fix:`) unless schema/config compatibility is intentionally broken.

- Use `fix:` for normal maintenance and safe behavior changes.
- Use `feat:` only for additive, backward-compatible functionality.
- Use `!` / `BREAKING CHANGE` when changing `.metagit.yml` or app config schema in a non-backward-compatible way.

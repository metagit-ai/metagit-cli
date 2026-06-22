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
- Idempotent additive (CI-safe): `metagit project source sync --provider github --org <org> --mode additive --ensure --apply`
- Refresh metadata with ensure: add `--refresh-metadata` to update descriptions/tags on existing URLs
- Filters: repeatable `--ignore '**/deprecated/**'` and `--include-pattern 'acme/platform-*'`
- Agent JSON: append `--json` (logs stay on stderr when not using JSON-only tooling)
- Clone after apply: `--sync` runs `metagit project sync` for the target project
- Agent alias: `metagit workspace import --project <p> --provider github --org <org> [--ignore ...]`
- MCP (ACTIVE): `metagit_project_source_sync` with the same parameters (`apply`, `confirm`, `sync`)
- Reconcile apply: `metagit project source sync --provider gitlab --group <group> --mode reconcile --apply --yes`

### Declarative `sources[]` (manifest sync)

Store import scopes on `workspace.projects[].sources[]` and sync from the manifest instead of CLI flags:

```yaml
workspace:
  projects:
    - name: platform
      sources:
        - id: github-platform
          provider: github
          org: acme
          mode: additive
          ensure: true
          ignore:
            - "**/archived/**"
      repos: []
```

- Manifest sync: `metagit project --project platform source sync --from-manifest --apply --json`
- Single source: `--source-id github-platform`
- Persist imperative flags: `--write-source --source-id github-platform` (after a successful imperative sync)
- Project sync hook: `metagit project sync --project platform --refresh-sources` (manifest sync then git sync)
- Reconcile removals are deferred unless `--force`; pending removals enqueue `source_sync_reconcile` approvals — approve with `metagit context approval approve --id <id>`
- Repos without `source_id` are manual entries and are never auto-removed during reconcile

**Web:** Config Studio edits `sources[]`; Workspace Console Operations panel runs manifest sync and resolves approvals. See [metagit-web.md](reference/metagit-web.md).

## Modality parity

Operator-facing features should share core services across CLI, MCP, and web. When adding capability:

1. Put logic in `src/metagit/core/…` (not in Click handlers or React alone).
2. Wire adapters for each modality in the same change when possible.
3. Register markers in `scripts/modality-parity.yml`; `task qa:prepush` runs `scripts/check_modality_parity.py`.
4. Follow `.mex/patterns/modality-parity.md`.

GitHub org/user listing is flat (no nested subgroups). GitLab groups honor `--recursive` / `--no-recursive` for subgroups. Default manifest naming is `namespaced`; use `--name-strategy short` for legacy short names.

| Flag combo | Re-run behavior |
|------------|-----------------|
| `--mode additive --apply` | Add missing; update changed metadata |
| `--mode additive --apply --ensure` | Add missing; noop for existing URLs |
| `--ensure --refresh-metadata` | Ensure plus provider metadata refresh |

## Changelog and releases

- Maintain user-facing changes under `## Unreleased` in root `CHANGELOG.md`.
- `task qa:prepush` and CI run `scripts/validate_changelog.py` when `src/`, `schemas/`, or `web/` change. Set `SKIP_CHANGELOG_CHECK=1` to bypass locally.
- The docs site publishes the same file at `/changelog/` — `task docs` and the docs workflow sync `CHANGELOG.md` into `docs/changelog.md` before `mkdocs build`.

## Semantic Release Tags

`.github/workflows/semantic-release.yaml` runs on merges to `main` and uses conventional commit prefixes to compute the next version.

- Promotes `## Unreleased` into a dated version section in `CHANGELOG.md`, commits to `main`, then tags.
- Tags created by the workflow use the canonical `vX.Y.Z` format.
- GitHub Release notes use the promoted changelog body (commit-log fallback only when `Unreleased` is empty).
- Changelog-only commits do not retrigger semantic release, and no tag is created when there are no releasable `fix:`, `feat:`, or breaking-change commits since the previous tag.
- The workflow currently floors computed release versions at `0.8.0` so the next valid release lands on `v0.8.0` or newer instead of continuing the accidental `0.7.x` line.
- Release automation is deterministic (no LLM). GitHub Copilot AI credits are not a free pipeline for custom workflows; they meter Copilot Chat/agents/review features instead.

- `fix:` -> patch release (`X.Y.Z+1`) **default for most updates**
- `feat:` -> minor release (`X.Y+1.0`)
- `type(scope)!:` or `BREAKING CHANGE:` -> major release (`X+1.0.0`)

### Commit Prefix Guidance

Use patch semantics first (`fix:`) unless schema/config compatibility is intentionally broken.

- Use `fix:` for normal maintenance and safe behavior changes.
- Use `feat:` only for additive, backward-compatible functionality.
- Use `!` / `BREAKING CHANGE` when changing `.metagit.yml` or app config schema in a non-backward-compatible way.

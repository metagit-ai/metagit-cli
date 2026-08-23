---
name: provider-ci-target-extension
description: Extending source sync providers and durable ProjectPath.ci topology for agents.
last_updated: 2026-08-20
---

# Provider + CI target extension

## When to use

Adding a new git host as a declarative `sources[]` provider and/or durable CI topology for orchestrators.

## Steps

1. Add `SourceProvider` enum value + `SourceSpec`/`ProjectSource` scope fields and validators.
2. Implement `_discover_<provider>` in `SourceSyncService` (listing stays in source sync, not `GitProvider`).
3. Add AppConfig provider block + `METAGIT_*` env overrides.
4. Optionally register a `GitProvider` subclass for URL handle + metadata enrichment.
5. For CI topology: extend `CiTargetResolver` remote parse + `ci-files.json` labels; keep `ProjectPath.ci` as the durable binding.
6. Wire CLI/MCP/web parity; regenerate schemas (`task generate:schema`).
7. Live pipeline status (web CI/CD tab) should consume `ProjectPath.ci` before URL fallback — do not invent a second binding model.

## Gotchas

- Azure DevOps remotes are `org/project/_git/repo` (HTTPS) or `v3/org/project/repo` (SSH); do not treat as GitHub-style `owner/repo`.
- Do not clobber `ci.status` of `declared`/`overridden` on re-detect without `--force`.
- Omit empty `ci` from manifests to keep fmt defaults lean.

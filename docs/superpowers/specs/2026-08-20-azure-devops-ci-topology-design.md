# Azure DevOps Source + Agent CI Topology — Design Spec

**Date:** 2026-08-20  
**Status:** Accepted (implementation)  
**Builds on:** Provider source import ([2026-06-11](2026-06-11-provider-source-import-design.md)), workspace context packs, live `PipelineStatusService` (GitHub/GitLab only today)

## Problem

Orchestrators need a fast, durable answer for each managed repo:

- Which CI platform owns this repo?
- Which config files declare pipelines?
- For Azure DevOps: which organization / project / repository (and optionally definition) to query later?

Live pipeline status today only covers GitHub Actions and GitLab CI via remote host substring. Source sync only supports `github` | `gitlab`. Static `ci-files.json` already maps `azure-pipelines.yml`, but nothing promotes that into workspace metadata or context packs.

ADO remotes are `org/project/_git/repo` (HTTPS) or `v3/org/project/repo` (SSH). Pipelines can live in a different ADO project than the git repo — URL-only inference is necessary but not always sufficient.

## Sequencing

| Phase | Scope |
|-------|--------|
| **1A** | Durable CI topology (`ProjectPath.ci`) + agent surfaces |
| **1B** | Azure DevOps as declarative repo source |
| **2** | Live ADO pipeline monitoring in the web CI/CD tab (consumes Phase 1A bindings) |

Phase 2 must not invent a second binding model. Live status prefers declared/detected `ci`, then falls back to remote URL parsing.

## Design decision: per-repo `ci` on `ProjectPath`

Optional `RepoCiTarget` on workspace `ProjectPath` (not monorepo path-scoped targets in v1).

### Shape

- `provider`: `github` | `gitlab` | `azure_devops` | `other` | `none` | `unknown`
- `config_paths`: list of repo-relative CI config paths
- `host`: optional API/web host (self-hosted ADO)
- Locators: ADO `organization` / `project` / `repository` + optional `definition_ids`; GitHub `owner` / `name`; GitLab `project_path`
- `status`: `detected` | `declared` | `overridden`
- `updated_at`: optional ISO timestamp

Re-detect must not clobber `declared` or `overridden` without `--force`.

Leaf `.metagit.yml` `cicd` is **not** dual-written in Phase 1 — workspace `ProjectPath.ci` is the orchestrator source of truth.

### Resolution

`CiTargetResolver.resolve(repo_path, url, existing_ci, force=False)`:

1. Preserve `declared` / `overridden` unless force.
2. Parse remote → provider + locator (ADO hosts included).
3. Scan known CI files (`ci-files.json` patterns).
4. Merge file platform + remote locator + `config_paths`.
5. Omit empty `ci` from manifests when nothing useful is found.

### Surfaces

- CLI: `metagit project repo ci show|detect|set`
- MCP: `metagit_repo_ci_show` / `metagit_repo_ci_detect`
- Context: `ci` summary on `RepoCardResult` / tier-1 packs

## Phase 1B — Azure DevOps source

| Field | Meaning |
|-------|---------|
| `organization` | Required |
| `project` | Optional filter |
| `recursive` | When `project` unset: list repos across all projects in the org |

AppConfig `providers.azure_devops` (`enabled`, `api_token`, `base_url` default `https://dev.azure.com`) with `METAGIT_AZURE_DEVOPS_*` and `AZURE_DEVOPS_EXT_PAT` fallback. PAT auth via HTTP Basic (`:` + PAT).

Discovery stays in `SourceSyncService` (current if/elif pattern). Optional `AzureDevOpsProvider(GitProvider)` for URL handle + metadata enrichment.

On import, optionally attach detected `ci` from remote URL when no checkout is available yet.

## Phase 2 contract (deferred)

- Extend `PipelineStatusService` + CI/CD dashboard for `azure_devops`.
- Prefer `ProjectPath.ci` locator over re-parsing remote.
- Query Pipelines/Builds API; terrain beacons reuse existing pipeline rows.

## Non-goals

- Live pipeline polling in this change set
- Path-level monorepo CI ownership map
- Bitbucket or other hosts
- Full discovery-protocol refactor of `SourceSyncService`

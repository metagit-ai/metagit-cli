# MCP Phase 3 — Workspace Intelligence — Design Spec

**Status:** Implemented  
**Date:** 2026-05-15

## Tools

### `metagit_workspace_health_check`

Read-only workspace maintenance report.

| Parameter | Default |
|-----------|---------|
| `check_git_status` | true |
| `check_dependencies` | true |
| `check_stale_branches` | true (reserved; branch-age not implemented) |
| `check_gitnexus` | true |
| `project_name` | optional scope |

Returns `repos[]`, `recommendations[]` with `severity` and `action`, and `summary` counts.

### `metagit_workspace_discover`

File discovery (ripgrep `--files` when available).

| Parameter | Notes |
|-----------|-------|
| `intent` | `config`, `scripts`, `ci`, `docker`, `terraform` |
| `pattern` | Additional glob, e.g. `**/*.yml` |
| `repos` / `project_scope` | Repo or project selectors |
| `exclude_generated` | Skip vendor/lockfiles (default true) |
| `categorize` | Group results by category (default true) |

Requires `intent` or `pattern`.

### `metagit_project_template_apply`

| Parameter | Notes |
|-----------|-------|
| `template` | Name under `src/metagit/data/templates/` |
| `target_projects` | Workspace project names |
| `dry_run` | Default **true** |
| `confirm_apply` | Required when `dry_run` is false |

Skips files that already exist at the destination.

## Resources

- `metagit://workspace/health` — same payload as health check tool
- `metagit://workspace/context` — active project + session from `.metagit/sessions/`

## Bundled templates

- `agent-standard` — `AGENTS.md.fragment`, `.metagit/agent-notes.md`

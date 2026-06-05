---
name: metagit-workspace-sync
description: Sync workspace repositories safely using metagit with scoped fetch, pull, or clone actions. Use when repository content must be refreshed for implementation.
metadata:
  internal: true
---
# Syncing Workspace Repositories

Use this skill when repository state must be updated.

## Workflow

1. Confirm active workspace and target project.
2. Start with read-only status and fetch where possible.
3. Use pull/clone only when required for the current objective.
4. Summarize which repositories changed and what remains stale.

## Commands

- `metagit project sync --project <name>`
- MCP `metagit_workspace_sync` for batch fetch/pull/clone (`repos`, `only_if`, `dry_run`, `max_parallel`)
- MCP `metagit_repo_sync` for a single repository (requires `allow_mutation` for pull/clone)
- `./skills/metagit-control-center/scripts/control-cycle.sh [root_path] ["query"] [preset]`

## Output Contract

Return:
- repositories synced
- sync mode used (fetch/pull/clone)
- failures and retry guidance

## Safety

- Limit sync to repos defined in `.metagit.yml`.
- Avoid broad synchronization if only a subset is needed.

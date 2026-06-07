---
name: metagit-repo-impact
description: Plan repository change impact before edits by combining metagit workspace context and graph-based dependency analysis. Use when a change may affect multiple repositories.
---

# Planning Repo Impact

Use this skill before risky or cross-repo modifications.

## Workflow

1. Identify target symbols/files for change.
2. Use metagit workspace context to bound repository scope.
3. Use graph impact tooling to estimate blast radius.
4. Produce a change plan with test and rollback focus.

## Commands

- `metagit workspace select --project <name>`
- MCP `metagit_cross_project_dependencies` with `source_project` and `dependency_types` before large cross-project edits
- MCP `metagit_project_context_switch` to bound scope to one workspace project
- `npx gitnexus analyze` on affected repos when `graph_status` is `stale` or `missing`
- `metagit gitnexus group sync -c .metagit.yml` when cross-repo symbol impact is needed (after per-repo analyze)
- `npx gitnexus query` / `gitnexus impact` for single-repo symbol analysis; `gitnexus group impact` for cross-index

## Output Contract

Return:
- impacted repositories and interfaces
- highest-risk change points
- minimum validation plan

## Safety

- Do not execute mutating steps in this planning phase.

---
name: metagit-workspace-scope
description: Discover active metagit workspace scope, project boundaries, and repository status. Use when an agent starts work in a multi-repo workspace and needs fast, scoped context before editing.
---

# Discovering Workspace Scope

Use this skill at session start for workspace-aware tasks.

## Workflow

1. Run workspace gate and status checks first.
2. Read configured projects and repository status from metagit resources/tools.
3. Build a compact map of active project names, repo names, and sync state.
4. Report a bounded scope for the current objective.

## Commands

- `zsh ./skills/metagit-gating/scripts/gate-status.zsh [root_path]`
- `metagit workspace select --project <name>` (interactive repo picker)
- MCP `metagit_project_context_switch` with `project_name` (structured context + session restore)
- MCP `metagit_workspace_state_snapshot` before leaving a project for a long switch

## Output Contract

Return:
- active/inactive workspace state and reason
- candidate project to operate on
- top repositories to inspect first

## Safety

- Keep operations read-only in this step.
- Do not sync or mutate repositories without explicit request.

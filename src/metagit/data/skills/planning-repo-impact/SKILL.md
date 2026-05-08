---
name: planning-repo-impact
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
- `npx gitnexus query --help` (for dependency/flow exploration commands available in your environment)

## Output Contract

Return:
- impacted repositories and interfaces
- highest-risk change points
- minimum validation plan

## Safety

- Do not execute mutating steps in this planning phase.

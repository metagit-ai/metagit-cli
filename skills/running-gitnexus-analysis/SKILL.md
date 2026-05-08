---
name: running-gitnexus-analysis
description: Run gitnexus analysis for a target workspace and selected project repositories before graph-dependent tasks. Use when index staleness is detected or cross-repo graph results are needed.
---

# Running GitNexus Analysis

Use this skill whenever GitNexus context is stale or missing for target repositories.

## Local Wrapper (Use First)

- `zsh ./skills/running-gitnexus-analysis/scripts/analyze-targets.zsh <workspace_root> [project_name]`

## Workflow

1. Analyze the current repository where the command is run.
2. Resolve target project repositories from `.metagit.yml`.
3. Run `npx gitnexus analyze` in each local repository path found.
4. Report per-repository success/failure and next actions.

## Output Contract

Return:
- analyzed repositories
- failures and reasons
- whether graph queries are safe to run now

## Safety

- Skip repositories that do not exist locally.
- Do not mutate repo content; analysis should be read-only indexing.

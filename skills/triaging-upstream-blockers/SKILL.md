---
name: triaging-upstream-blockers
description: Triage cross-repository blockers by ranking likely upstream repositories and files with metagit search and hinting tools. Use when local fixes appear incomplete.
---

# Triaging Upstream Blockers

Use this skill for failures likely rooted in another repository.

## Workflow

1. Run workspace index and search with issue-specific terms.
2. Run upstream hint ranking to prioritize repositories/files.
3. Open the top candidates and validate root-cause evidence.
4. Return a short fix path (repo, file, next action).

## Command Wrapper

- `zsh ./skills/metagit-upstream-discovery/scripts/upstream-scan.zsh [root_path] "<query>" [preset] [max_results]`

## Output Contract

Return:
- ranked candidate repositories
- probable root-cause files
- confidence and assumptions

## Safety

- Keep this flow read-only unless sync is explicitly requested.

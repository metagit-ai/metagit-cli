---
name: metagit-multi-repo
description: Coordinate implementation tasks across multiple repositories using metagit status, search, and scoped sync workflows. Use when one objective spans several repositories.
metadata:
  internal: true
---
# Coordinating Multi-Repo Implementation

Use this skill for cross-repository feature or fix delivery.

## Workflow

1. Define objective and affected repositories.
2. Verify workspace scope and dependency hints.
3. Sequence work by dependency order.
4. Sync only required repositories.
5. When running **parallel agents** on the same repo, isolate with skill **`metagit-agent-coordination`** (branch → lease → worktree) before edits.
6. Track progress and blockers per repository.

## Command Wrapper

- `./skills/metagit-control-center/scripts/control-cycle.sh [root_path] ["query"] [preset]`

## Output Contract

Return:
- objective-to-repository map
- execution order
- current blocker + next step

## Safety

- Keep scope bounded to configured workspace repositories.
- Prefer deterministic evidence for cross-repo assumptions.

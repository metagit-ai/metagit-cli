---
name: session-worktree-coordination
description: Keep ACL merges and worktree gc from touching another checkout, and keep agent/* naming as the default.
edges:
  - target: agent-coordination-acl.md
    condition: when changing branch, lease, worktree, or claim behavior
last_updated: 2026-10-01
---

# Session worktree coordination

## When to use

Changing `branch allocate`, `merge integrate` / `promote`, or `worktree gc` / `destroy`.

## Do

1. Default branch names stay `agent/<task>[-slug]`. New schemes go through `coordination.allowed_branch_prefixes` and `coordination.branch_pattern`.
2. Merge in a temporary worktree. Never `checkout` in the caller's `repo_path`.
3. Refuse when the target branch is already checked out. Do not add a flag that moves that checkout.
4. `gc` and `destroy` skip dirty trees, untracked non-ignored files, and unpushed commits. The message names `--force`. `gc --dry-run` changes nothing.
5. Ignore `.metagit-agent.json` in the untracked check. It is written by `worktree create`.
6. Count unpushed commits only when the repo has a remote. Worktree removal does not delete the branch.

## Verify

```bash
uv run pytest tests/core/coordination/test_branch_prefixes.py tests/core/coordination/test_worktree_gc_safety.py tests/core/merge/test_isolated_integrate.py tests/core/merge/test_git_ops.py -q
```

Design: `docs/superpowers/specs/2026-10-01-session-worktree-coordination-design.md`.

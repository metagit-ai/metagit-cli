# Discovering worktrees

`metagit worktree list --discover` walks synced repositories in the composed manifest and reports every git worktree, including one created with `git worktree add`. Each record has the owning repo, branch, whether the tree is dirty or clean, how many commits it is ahead of its upstream, and `primary` for the repository's main checkout.

```bash
metagit worktree list --discover -c .metagit.yml
metagit worktree list --discover --pr --json -c .metagit.yml
```

`--pr` adds pull-request state from the forge API. When no token is set (`GH_TOKEN` or `GITHUB_TOKEN`), that field stays empty and the command does not fail.

`metagit worktree gc --merged` removes discovered worktrees that are clean and whose HEAD is the head of a merged or closed pull request. `--dry-run` lists them and deletes nothing. Dirty trees and the primary checkout are skipped. Removal never uses `git worktree remove --force`.

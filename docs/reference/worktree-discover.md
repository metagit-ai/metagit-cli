# Discovering worktrees

`metagit worktree list --discover` walks synced repositories in the composed manifest and reports every git worktree, including one created with `git worktree add`. A repo with `path` is read from that path. Otherwise the checkout is `<workspace>/<project>/<repo>`, where the workspace path is `METAGIT_WORKSPACE_PATH` or the app config path and defaults to `./.metagit` next to the manifest. Each record has the owning repo, branch, whether the tree is dirty or clean, how many commits it is ahead of its upstream, and `primary` for the repository's main checkout.

```bash
metagit worktree list --discover -c .metagit.yml
metagit worktree list --discover --pr --json -c .metagit.yml
```

`--pr` adds pull-request state from the forge API. The manifest repo `url` is tried first, then the checkout remote. An SSH host alias is resolved with `ssh -G`. When no token is set (`GH_TOKEN` or `GITHUB_TOKEN`), that field stays empty and the command does not fail. `--json` reports `pr_reason` as `no pull request`, `forge not supported`, or `lookup failed`. `worktree gc --merged --json` uses the same reason on each skipped worktree.

`metagit worktree gc --merged` removes discovered worktrees that are clean and whose HEAD is the head of a merged or closed pull request. `--dry-run` lists them and deletes nothing. Dirty trees and the primary checkout are skipped. Removal never uses `git worktree remove --force`.

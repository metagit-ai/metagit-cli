# Session-per-worktree coordination

Date: 2026-10-01

The coordination layer (`branch`, `lease`, `worktree`, `claim`, `merge`) should
support one git worktree and one branch per agent session in the repository
that holds `.metagit.yml`, then roll those branches into one integration
branch. Existing `agent/*` users keep today's behavior unless they opt in.

## Validity

Reviewed against the tree after 0.35.0. The 0.34.1 citations still match.

| Gap | Verdict |
| --- | --- |
| Branch names are hardcoded to `agent/` | True. `BranchService.allocate` rejected anything else. |
| `merge integrate` checks out the target in `repo_path` | True. `attempt_merge` called `checkout` then `merge`. `promote` uses the same helper. |
| `worktree gc` force-removes expired leases | True. Default lease TTL is `30m`, and `gc` called `destroy(force=True)`. |
| One worktree per agent per repo, path has no task id | True. |
| No repository ref for the manifest repo itself | True. Lookup is `project/repo`, a sync mount, or a manifest path. |
| New worktrees have no gitignored runtime files | True. `worktree add` does not copy or link anything. |
| Generated-file conflicts block merges | No metagit feature for this. The overlap count is outside this repo; the mechanism is still worth adding. |

Worth doing. The first three are safety bugs. The rest is the session workflow
and stays opt-in.

## Decisions

- Branch naming is AppConfig `coordination.branch_pattern` (default
  `agent/{task_id}[-{slug}]`) and `coordination.allowed_branch_prefixes`
  (default `["agent/"]`). `--name` is checked against the prefixes. A refusal
  names `coordination.allowed_branch_prefixes`.
- `integrate` and `promote` merge in a temporary worktree metagit creates and
  deletes. They never check out `repo_path`. If the target branch is checked
  out anywhere, they refuse. No flag overrides that refusal.
- Validators with a non-empty command list run in a detached worktree of the
  merge commit.
- `gc` and `destroy` skip uncommitted changes, untracked non-ignored files, and
  commits that are not on a remote. `--force` overrides. `gc --dry-run` only
  reports. A repo with no remotes is not treated as unpushed, because removing
  the worktree leaves the branch. `.metagit-agent.json` is coordination
  metadata and does not count as user work.
- Multiple worktrees per agent are opt-in. Default stays one active worktree
  per agent per repo at `.worktrees/<agent>/<project>/<repo>`. P2 adds
  `coordination.worktree_per_task` (default false). When true, the key is
  `(agent_id, repository, task_id)` and the checkout path includes the task id.

## Tiers

### P1 (this change)

Configurable prefixes, isolated integrate/promote, safe gc/destroy.
Acceptance tests 1–3.

### P2

- `coordination.worktree_per_task` for a second active worktree.
- Repository ref `.` and `self` resolve to the git top level of the definition
  root, for `branch`, `lease`, `worktree`, `claim`, and `merge`.
- `worktree adopt` registers rows from `git worktree list --porcelain` without
  creating another checkout.
- `coordination.worktree.post_create` entries: `symlink`, `copy`, or `run`.
  Symlink and copy targets must be gitignored. A tracked path is refused and
  the message names the config key.

Acceptance tests 4–6.

### P3

- `merge.regenerate` maps a path glob to a command. If every conflicted path
  matches, take the target side, run the command in the temporary integration
  worktree, stage the result, and continue. Any unmapped path stops as a
  conflict.
- `merge rollup --into <branch> --base <ref> --branches <glob-or-list>` creates
  the integration branch when missing, merges in order, runs validators after
  each merge, and stops at the first unresolvable conflict. The summary lists
  merged, skipped, and conflicted. Push and pull-request stay outside metagit.

Acceptance test 7.

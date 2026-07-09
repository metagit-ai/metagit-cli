# Agent Coordination Layer (RFC-0007)

<!-- modality:acl_branch -->
<!-- modality:acl_lease -->
<!-- modality:acl_worktree -->
<!-- modality:acl_claim -->
<!-- modality:acl_manifest -->

Metagit’s **Agent Coordination Layer (ACL)** provides Git-isolation and advisory
ownership primitives so many agents can work across repositories without sharing
checkouts or colliding on the same branch.

This is **not** the same as handoff claim TTL leases
(`metagit context handoff claim --ttl`). Handoff leases own a *task queue row*.
ACL leases own a *branch* for an agent.

## Principles

1. Agents never share worktrees.
2. Agents never share `agent/*` working branches.
3. Branch leases expire and can be renewed.
4. File claims and repo presence are **advisory** — Git remains the authority.
5. Task graphs, merge orchestration, semantic ownership, and scheduling are
   deferred to RFC-0008+.

## Persistence

Under the session/manifest root:

```text
.metagit/
  branches/branches.json
  leases/leases.json
  worktrees/worktrees.json
  claims/claims.json
  presence/presence.json
  agents/<agent-id>.json
  events/acl.jsonl
.worktrees/<agent-id>/<project>/<repo>/   # default; configurable
```

Checkout directory is controlled by appconfig `workspace.worktrees_path`
(default `.worktrees`, env `METAGIT_WORKSPACE_WORKTREES_PATH`). Relative values
resolve from the manifest/session root. The path basename (and the same name
without a leading `.` / `_`) is reserved and cannot be used as a workspace
project name.

## CLI

```bash
# Allocate an agent branch
metagit branch allocate --repository project/repo --agent-id agent-1 --task-id 412 --description auth

# Lease the branch (default TTL 30m)
metagit lease acquire --repository project/repo --agent-id agent-1 --task-id 412 --branch agent/412-auth

# Or allocate + lease in one step
metagit lease acquire --repository project/repo --agent-id agent-1 --task-id 412 --allocate

metagit lease renew --lease-id <id> --agent-id agent-1 --ttl 1h
metagit lease release --lease-id <id> --agent-id agent-1
metagit lease list --repository project/repo --json

# Isolated worktree (requires active lease)
metagit worktree create --repository project/repo --agent-id agent-1 --task-id 412 --branch agent/412-auth
metagit worktree status --agent-id agent-1 --json
metagit worktree manifest agent-1
metagit worktree destroy --worktree-id <id> --force
metagit worktree gc

# Advisory file claims
metagit claim declare --repository project/repo --agent-id agent-1 --pattern 'backend/auth/*'
metagit claim check --repository project/repo --pattern 'backend/auth/token.py'
metagit claim list --repository project/repo --json
metagit claim release --claim-id <id> --agent-id agent-1
```

## MCP tools

When the workspace gate is ACTIVE:

| Tool | Purpose |
|------|---------|
| `metagit_branch_allocate` / `list` / `release` | Branch allocations |
| `metagit_lease_acquire` / `renew` / `release` / `list` | Branch leases |
| `metagit_worktree_create` / `destroy` / `status` / `list` | Worktrees |
| `metagit_claim_declare` / `check` / `list` / `release` | File claims |

## Events

ACL lifecycle events append to `.metagit/events/acl.jsonl` and appear in
`metagit context events` with `source: acl` (kinds such as `BranchAllocated`,
`LeaseGranted`, `LeaseExpired`, `WorktreeCreated`, `ClaimConflict`).

## Dispatch hints

`metagit agent dispatch-plan` includes `handoff.acl_commands` when project and
repo are set — suggested allocate / lease / worktree / claim CLI strings only
(no automatic mutation).


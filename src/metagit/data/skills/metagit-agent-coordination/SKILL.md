---
name: metagit-agent-coordination
description: >-
  Isolate concurrent agents with RFC-0007 ACL primitives: allocate agent/*
  branches, acquire branch leases, create exclusive git worktrees, and declare
  advisory file claims. Use when launching multiple agents, avoiding shared
  checkouts, preventing branch collisions, or coordinating file ownership
  before coding. Distinct from handoff claim TTL leases.
metadata:
  internal: true
---
# Metagit Agent Coordination Layer (ACL)

Use when **more than one agent** may edit the same repository, or when an
orchestrator must give each agent an exclusive checkout.

Full reference: [docs/reference/agent-coordination.md](../../../../docs/reference/agent-coordination.md)

<!-- modality:acl_branch -->
<!-- modality:acl_lease -->
<!-- modality:acl_worktree -->
<!-- modality:acl_claim -->
<!-- modality:acl_manifest -->
<!-- modality:task_graph -->
<!-- modality:semantic_ownership -->
<!-- modality:merge_orchestrator -->
<!-- modality:agent_scheduler -->

Task graphs (`metagit task …`) can store ACL command hints on nodes via
`metagit task bind-acl` without running git — see
[docs/reference/task-graph.md](../../../../docs/reference/task-graph.md).

Merge orchestration (`metagit merge …`) records conflicts with ACL command
hints only; it does not allocate branches or worktrees automatically.

The agent scheduler (`metagit schedule next`) scores ready task nodes and
returns dispatch hints without launching models or mutating git — see
[docs/reference/agent-scheduler.md](../../../../docs/reference/agent-scheduler.md).

## When to use

- Dispatching parallel subagents on the same repo
- `handoff.acl_commands` appears in `metagit agent dispatch-plan`
- Preventing two agents from sharing a working directory
- Declaring intended file paths before coding (advisory claims)
- Cleaning up expired leases / orphan worktrees

## Do not confuse with handoff leases

| Concept | Command | Owns |
|---------|---------|------|
| **Handoff claim TTL** | `metagit context handoff claim --ttl` | Task-queue row |
| **ACL branch lease** | `metagit lease acquire` | `agent/*` branch |

## Happy path

```bash
export METAGIT_AGENT_MODE=true

# 1. Allocate an exclusive agent branch
metagit branch allocate \
  --repository project/repo \
  --agent-id agent-1 \
  --task-id 412 \
  --description auth \
  --json

# 2. Lease it (default TTL 30m; renew while working)
metagit lease acquire \
  --repository project/repo \
  --agent-id agent-1 \
  --task-id 412 \
  --allocate \
  --ttl 30m \
  --json

# 3. Create an isolated worktree (requires active lease)
metagit worktree create \
  --repository project/repo \
  --agent-id agent-1 \
  --task-id 412 \
  --branch agent/412-auth \
  --json

# 4. Optional: advisory file claims before editing
metagit claim declare \
  --repository project/repo \
  --agent-id agent-1 \
  --pattern 'src/auth/*' \
  --json

# 5. Show execution manifest written on create
metagit worktree manifest agent-1
```

Or allocate + lease in one step with `--allocate` on `lease acquire`.

## Paths

- **Metadata:** `.metagit/{branches,leases,worktrees,claims,agents,events}/` under the manifest/session root
- **Checkouts:** `<session-root>/<worktrees_path>/<agent-id>/<project>/<repo>/`
  - Default `worktrees_path`: `.worktrees`
  - Appconfig: `workspace.worktrees_path`
  - Env: `METAGIT_WORKSPACE_WORKTREES_PATH`
- Path basenames (e.g. `worktrees`, `.worktrees`, `campaigns`, `_campaigns`) are **reserved** and cannot be workspace project names

## MCP tools (ACTIVE gate)

| Area | Tools |
|------|-------|
| Branch | `metagit_branch_allocate`, `metagit_branch_list`, `metagit_branch_release` |
| Lease | `metagit_lease_acquire`, `metagit_lease_renew`, `metagit_lease_release`, `metagit_lease_list` |
| Worktree | `metagit_worktree_create`, `metagit_worktree_destroy`, `metagit_worktree_status`, `metagit_worktree_list` |
| Claim | `metagit_claim_declare`, `metagit_claim_check`, `metagit_claim_list`, `metagit_claim_release` |

Events appear in `metagit context events` / `metagit_events` with `source=acl`.

## Conflict handling

- **Branch already allocated** — choose a different `task-id` / description, or wait for release
- **Lease held by another agent** — wait, renew is owner-only; do not force unless authorized
- **Claim overlap** — advisory; response includes `owner` + overlapping patterns; subdivide, wait, or override with `--strict` off (default allows declare with conflict event)
- **Worktree already exists for agent+repo** — destroy/gc first; one active worktree per `(agent_id, repository)`

## Cleanup

```bash
metagit lease renew --lease-id <id> --agent-id agent-1 --ttl 1h
metagit lease release --lease-id <id> --agent-id agent-1 --release-branch
metagit worktree destroy --worktree-id <id> --force
metagit worktree gc
metagit branch cleanup
```

## Anti-patterns

- Two agents editing the same sync-root checkout
- Using handoff `--ttl` instead of `metagit lease` for branch ownership
- Naming a workspace project `worktrees` or `campaigns`
- Skipping lease acquire before `worktree create`
- Leaving expired leases / orphan worktrees without `gc`

## Related skills

- `metagit-control-center` — orchestrator dispatch; run this skill when isolating subagents
- `metagit-multi-repo` — cross-repo delivery; use ACL per repo before parallel edits
- `metagit-sharing-state` — shared objectives/handoffs across machines (orthogonal to git isolation)
- `metagit-cli` — short ACL command cheat sheet

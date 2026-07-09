---
name: agent-coordination-acl
description: Implement or extend RFC-0007 Agent Coordination Layer primitives (branch, lease, worktree, claim).
edges:
  - target: ../context/architecture.md
    condition: when placing new coordination services
  - target: modality-parity.md
    condition: when exposing CLI/MCP surfaces
last_updated: 2026-07-09
---

# Agent Coordination Layer (ACL)

## When to use

Adding or changing worktree/branch/lease/claim behavior for multi-agent Git isolation.

## Do

1. Put logic in `src/metagit/core/coordination/` — thin CLI/MCP adapters only.
2. Persist under session-root `.metagit/{branches,leases,worktrees,claims,agents,events}/`.
3. Keep ACL branch leases distinct from handoff claim TTL (`HandoffService`).
4. Emit typed events via `AclEventStore` so `WorkspaceEventService` surfaces `source=acl`.
5. Register modality features in `scripts/modality-parity.yml`.
6. Prefer GitPython for worktree/branch ops; advisory claims never block git.

## Don't

- Don't implement task DAG, merge orchestrator, or semantic ownership here (later RFCs).
- Don't put agent worktrees under the sync-root catalog mounts.
- Don't share one worktree across agents.

## Verify

```bash
uv run pytest tests/core/coordination/ tests/cli/commands/test_acl_cli.py -q
task qa:prepush
```

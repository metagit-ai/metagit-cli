---
name: task-graph-intent
description: Implementing or extending RFC-0008 task DAG + intent under metagit.core.taskgraph
last_updated: 2026-07-09
---

# Task Graph & Intent (RFC-0008)

## When to use

- Adding task graph models, store, ready-set, CLI `metagit task`, or MCP `metagit_task_*`
- Wiring `source=taskgraph` into the workspace event feed
- Extending ACL bind hints without auto-running git

## Steps

1. Keep business logic in `src/metagit/core/taskgraph/`; CLI/MCP stay thin.
2. Persist under session root `.metagit/tasks/` (graphs + index); events in `.metagit/events/taskgraph.jsonl`.
3. Reject cycles and unknown deps at expand/write time; compute ready-set from completed deps.
4. `bind_acl` stores command strings only — never call branch/lease/worktree/claim from status transitions.
5. Register modality feature `task_graph` in `scripts/modality-parity.yml` and keep docs/skills markers in sync.
6. Tests: `tests/core/taskgraph/`, `tests/cli/commands/test_task_cli.py`, MCP smoke in `tests/core/mcp/test_task_tools.py`.

## Gotchas

- ACL branch leases ≠ handoff claim TTL.
- Many graphs per workspace; campaign expand and LLM outline expansion are out of scope for 0008.
- GitNexus impact before editing shared symbols (`WorkspaceEventService`, MCP runtime).

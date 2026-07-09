# Task Graph & Intent Engine (RFC-0008)

<!-- modality:task_graph -->

Metagit’s **task graph** expands workspace objectives and handoffs into a DAG of
independently executable nodes. Ready nodes can store RFC-0007 ACL command hints
(branch / lease / worktree / claim) without auto-running git.

This is **not** the scheduler (RFC-0012), context compiler (RFC-0009), merge
orchestrator (RFC-0011), or semantic ownership graph (RFC-0010).

## Persistence

Under the session/manifest root:

```text
.metagit/
  tasks/
    graphs/<graph_id>.json
    index.json
  events/taskgraph.jsonl
```

## CLI

```bash
metagit task create --title "Ship auth" --goal "…" [--objective-id …] [--json]
metagit task expand --graph-id … --from-outline outline.txt
# or: cat outline.json | metagit task expand --graph-id … --json

metagit task list [--graph-id …] [--status ready] [--json]
metagit task status --node-id … [--graph-id …] [--json]
metagit task ready [--graph-id …] [--json]
metagit task start --node-id …
metagit task block --node-id … --reason "…"
metagit task complete --node-id …
metagit task bind-acl --node-id … --agent-id agent-1 [--json]
```

Outline input may be:

- Indented text (indent implies parent dependency)
- JSON list of `{title, node_id?, depends_on?}`

Cycles and unknown dependency ids are rejected at write time.

## MCP tools

When the workspace gate is ACTIVE:

| Tool | Purpose |
|------|---------|
| `metagit_task_create` | Create graph + root intent |
| `metagit_task_expand` | Add nodes from outline/JSON |
| `metagit_task_list` | List graphs or nodes |
| `metagit_task_status` | One node |
| `metagit_task_ready` | Ready-set |
| `metagit_task_block` / `complete` | Status transitions |
| `metagit_task_bind_acl` | Store ACL CLI hints (no git) |

## Events

Lifecycle events append to `.metagit/events/taskgraph.jsonl` and appear in
`metagit context events` with `source: taskgraph` (kinds such as
`TaskGraphCreated`, `TaskNodeCreated`, `TaskReady`, `TaskBlocked`,
`TaskCompleted`, `TaskCancelled`, `TaskStarted`).

## ACL binding

`metagit task bind-acl` only stores suggested `acl_commands` (and optional ids).
Agents still run `metagit branch|lease|worktree|claim` explicitly — see
[agent-coordination.md](agent-coordination.md).

## Related

- Series index: [ACL RFC series](../superpowers/specs/2026-07-09-acl-rfc-series-index.md)
- Context compiler: [context-compiler.md](context-compiler.md) (RFC-0009)
- Skill: `metagit-agent-coordination` (ACL); task CLI also listed in `metagit-cli`

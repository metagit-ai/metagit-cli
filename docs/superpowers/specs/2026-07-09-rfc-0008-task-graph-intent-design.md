# RFC-0008: Task Graph & Intent Engine — Design

**Status:** Draft  
**Date:** 2026-07-09  
**Series:** [ACL RFC series index](2026-07-09-acl-rfc-series-index.md)  
**Vision:** [agent-coordination.md](../../reference/agent-coordination.md) (RFC-0007 vision; original spec.md retired) § Task Graph, Agent Manifest, Intent  
**Depends on:** RFC-0007 ACL (shipped)  
**Plan:** [2026-07-09-rfc-0008-task-graph-intent.md](../plans/2026-07-09-rfc-0008-task-graph-intent.md)

## Summary

Introduce a first-class **task DAG** and **intent** model so workspace objectives and handoffs can expand into independently executable nodes. Each ready node may bind RFC-0007 ACL primitives (branch, lease, worktree, claims) without inventing new lease semantics. Completion unlocks downstream nodes and emits typed events.

## Goals

- Represent work as a DAG of `TaskNode`s under a `TaskGraph`, linked to existing `Objective` / `HandoffItem` parents when present.
- Persist graphs under session/manifest root `.metagit/tasks/`.
- Expose CLI + MCP for create, expand, list, status, ready, block, complete.
- Optionally bind ACL resources to a node (store ids + suggested `acl_commands`; orchestrator still runs allocate/lease/worktree/claim).
- Emit lifecycle events into the workspace event feed (`source=taskgraph`).
- Keep intent structured: goal text, acceptance criteria, optional repo/project scope.

## Non-Goals

- Scheduler policy / “what runs next” (RFC-0012).
- Context compilation budgets (RFC-0009) beyond storing optional `context_budget` on the node/manifest.
- Semantic concept ownership (RFC-0010).
- Merge / integration-branch pipeline (RFC-0011).
- AOS composition façade (RFC-0013).
- SPA UI; SQLite/Postgres.
- Auto-mutating git or ACL on graph transitions (hints and stored bindings only unless explicitly invoked).

## Architecture

```text
Objective / Handoff (existing)
        │
        ▼
   TaskGraphService  ──►  .metagit/tasks/
        │
        ├── TaskIntent (goal, acceptance, scope)
        ├── TaskNode (status, deps, acl bindings)
        └── ready-set computation (deps satisfied)
        │
        ├── optional ACL bind ──► coordination/* (0007)
        └── events ──► WorkspaceEventService (source=taskgraph)
```

**Package:** `src/metagit/core/taskgraph/` (new), thin CLI/MCP adapters.

**Reuse:**
- Session root resolution (`root_resolver`) — same as ACL/handoffs.
- JSON store + file lock pattern from `coordination/store.py` (copy or share helper; do not couple packages tightly).
- `AgentExecutionManifest.task_id` / `dependencies` already exist — task graph becomes the authoritative id space over time.
- Dispatch plan may later include `handoff.task_commands` (optional in this RFC; prefer documenting extension point).

## Interfaces

### Models (proposed)

- `TaskIntent`: `intent_id`, `title`, `goal`, `acceptance: list[str]`, `project`, `repos: list[str]`, `objective_id?`, `handoff_id?`, timestamps
- `TaskNodeStatus`: `pending | ready | blocked | running | completed | cancelled`
- `TaskNode`: `node_id`, `graph_id`, `intent_id?`, `title`, `depends_on: list[str]`, `status`, `blocker_reason?`, `project?`, `repository?`, `agent_id?`, `acl: TaskAclBinding?`, timestamps
- `TaskAclBinding`: `branch?`, `lease_id?`, `worktree_id?`, `claim_ids: list[str]`, `acl_commands: list[str]`
- `TaskGraph`: `graph_id`, `title`, `root_intent_id?`, `objective_id?`, `nodes: list[TaskNode]`, `status`, timestamps

### CLI (proposed)

```bash
metagit task create --title "…" --goal "…" [--objective-id …] [--json]
metagit task expand --graph-id … --from-outline PATH|STDIN   # deterministic outline → nodes
metagit task list [--graph-id …] [--status ready] [--json]
metagit task status --node-id … [--json]
metagit task ready [--graph-id …] [--json]
metagit task block --node-id … --reason "…"
metagit task complete --node-id …
metagit task bind-acl --node-id … --agent-id …   # generate/store acl_commands + optional ids after user ran ACL
```

Exact flag names may adjust during implementation; keep `--json` and agent_mode-safe defaults.

### MCP (proposed)

`metagit_task_create`, `metagit_task_expand`, `metagit_task_list`, `metagit_task_status`, `metagit_task_ready`, `metagit_task_block`, `metagit_task_complete`, `metagit_task_bind_acl` — gated like other workspace tools.

### Expand semantics (v1)

- Input: indented outline or JSON list of `{title, depends_on?}`.
- No LLM required in core path; optional later sampling is out of scope for foundation.
- Cycles rejected at write time.

## Persistence

```text
.metagit/tasks/
  graphs/<graph_id>.json
  index.json          # optional lightweight listing
  events/taskgraph.jsonl   # or append via shared event store pattern
```

## Events

| Kind | When |
|------|------|
| `TaskGraphCreated` | graph created |
| `TaskNodeCreated` | node added |
| `TaskReady` | deps satisfied / status → ready |
| `TaskBlocked` | explicit block or unmet policy |
| `TaskCompleted` | node completed; may unlock dependents |
| `TaskCancelled` | cancelled |

Surface via `metagit context events` with `source=taskgraph`.

## Acceptance

- Create a graph with ≥3 nodes and edges; `ready` returns only roots; completing a root unlocks children.
- Cycle in expand/create fails with clear error.
- Node can store ACL binding without calling git.
- Unit tests for DAG ready-set; CLI `--json` smoke; modality features registered.
- Docs: `docs/reference/task-graph.md` + skill cross-links; series index status → In progress/Shipped when done.

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| RFC-0007 ACL, Objective/Handoff models | RFC-0009 (task identity), 0010 (node scope), 0011 (completed nodes → merge), 0012 (ready queue), 0013 (compose) |

## Open questions

1. Should `expand` accept campaign repo lists as a first-class source, or only outlines?
2. Is `running` set only by scheduler (0012) or also by explicit `task start` in 0008?
3. Single active graph per objective vs many?

**Recommendation for plan:** support many graphs; add optional `task start` that sets `running` without scheduler; campaign expand deferred.

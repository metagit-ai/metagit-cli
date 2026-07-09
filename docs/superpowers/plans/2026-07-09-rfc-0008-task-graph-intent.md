# RFC-0008 Task Graph & Intent Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a local task DAG + intent engine that expands objectives/handoffs into executable nodes, computes ready sets, binds optional ACL hints, and emits `source=taskgraph` events — without scheduler, merge, semantic KG, or context compiler.

**Architecture:** New `src/metagit/core/taskgraph/` package (models, paths, JSON store, `TaskGraphService`). Thin Click CLI `metagit task` and MCP tools. Reuse session-root resolution and the coordination JSON lock pattern. ACL binding stores ids/commands only; git mutations stay in RFC-0007 commands.

**Tech Stack:** Python, Pydantic, Click, MCP runtime, existing event feed, pytest.

**Design:** [2026-07-09-rfc-0008-task-graph-intent-design.md](../specs/2026-07-09-rfc-0008-task-graph-intent-design.md)  
**Series:** [acl-rfc-series-index](../specs/2026-07-09-acl-rfc-series-index.md)

## Global constraints

- Modality: CLI + MCP + core + docs/skills; no SPA; no `/v3/ops` unless remote-state sharing is required mid-MR.
- Persistence: `.metagit/tasks/` under session/manifest root only.
- Do not auto-run `branch|lease|worktree|claim` on status transitions.
- Many graphs per workspace; optional `task start` sets `running`; campaign expand deferred.
- ACL branch leases ≠ handoff claim TTL.
- Before editing symbols: GitNexus impact when available; always `task qa:prepush` before hand-off.

## File map (create)

| Path | Responsibility |
|------|----------------|
| `src/metagit/core/taskgraph/__init__.py` | Exports |
| `src/metagit/core/taskgraph/models.py` | `TaskIntent`, `TaskNode`, `TaskGraph`, `TaskAclBinding`, statuses |
| `src/metagit/core/taskgraph/paths.py` | Resolve `.metagit/tasks/` |
| `src/metagit/core/taskgraph/store.py` | Load/save graphs with file lock |
| `src/metagit/core/taskgraph/service.py` | create/expand/ready/block/complete/start/bind_acl |
| `src/metagit/core/taskgraph/events.py` | Append taskgraph events |
| `src/metagit/cli/commands/task.py` | Click group |
| `tests/core/taskgraph/` | Unit tests |
| `tests/cli/commands/test_task_cli.py` | CLI tests |
| `docs/reference/task-graph.md` | Operator reference |
| `.mex/patterns/task-graph-intent.md` | Recurring runbook |

## File map (modify)

- `src/metagit/cli/main.py` — register `task`
- `src/metagit/core/mcp/runtime.py` + tool registry — task tools
- `src/metagit/core/context/event_service.py` — merge `source=taskgraph`
- `scripts/modality-parity.yml` — `task_graph_*` features
- `docs/agents.md`, `llms.txt`, `AGENTS.md`, `CHANGELOG.md`, skills cross-links
- `.mex/ROUTER.md`, series index status
- `docs/reference/agent-coordination.md` — link to task-graph doc

---

### Task 1: Models + paths + store

**Files:** create `models.py`, `paths.py`, `store.py`, `__init__.py`; tests under `tests/core/taskgraph/test_models.py`, `test_store.py`

- [x] **Step 1: Write failing tests** for `TaskGraph` / `TaskNode` validation (slug ids, status enum) and store round-trip in a temp dir.
- [x] **Step 2: Run tests — expect fail** (`uv run pytest tests/core/taskgraph/test_taskgraph_models.py tests/core/taskgraph/test_store.py -q`).
- [x] **Step 3: Implement models, paths, store** (`T | Exception` returns; file lock).
- [x] **Step 4: Run tests — expect pass**.
- [ ] **Step 5: Commit** `feat(taskgraph): add models and JSON store for RFC-0008` (deferred — commit when user requests).

---

### Task 2: Ready-set + cycle detection in service

**Files:** create `service.py`; test `test_service_dag.py`

- [x] **Step 1: Write failing tests** — diamond DAG ready roots; complete unlocks children; cycle rejected on expand/add.
- [x] **Step 2: Run tests — expect fail**.
- [x] **Step 3: Implement `TaskGraphService`** create graph, add nodes, expand from outline/JSON, `ready()`, `complete()`, `block()`, `start()`.
- [x] **Step 4: Run tests — expect pass**.
- [ ] **Step 5: Commit** `feat(taskgraph): DAG ready-set and expand with cycle checks` (deferred).

---

### Task 3: Events

**Files:** create `events.py`; modify event_service; test event merge

- [x] **Step 1: Write failing test** that completing a node appends `TaskCompleted` visible to event poll with `source=taskgraph`.
- [x] **Step 2: Implement event append + wire into `WorkspaceEventService`**.
- [x] **Step 3: Tests pass;** commit deferred.

---

### Task 4: ACL bind (hints only)

**Files:** extend service + models; test `test_bind_acl.py`

- [x] **Step 1: Failing test** — `bind_acl` fills `acl_commands` strings for allocate/lease/worktree/claim using node project/repo/agent/task ids; no git calls.
- [x] **Step 2: Implement; tests pass;** commit deferred.

---

### Task 5: CLI `metagit task`

**Files:** `cli/commands/task.py`, `main.py`, `tests/cli/commands/test_task_cli.py`

- [x] **Step 1: Failing CLI tests** for create/expand/ready/complete/list `--json` using temp session root.
- [x] **Step 2: Implement Click group; register in main**.
- [x] **Step 3: Tests pass;** commit deferred.

---

### Task 6: MCP tools + modality parity

**Files:** tool registry, runtime dispatch, `scripts/modality-parity.yml`, MCP tests

- [x] **Step 1: Register tools** mirroring CLI; gate ACTIVE.
- [x] **Step 2: Parity YAML features** + markers in docs/skills as needed.
- [x] **Step 3: Tests;** commit deferred.

---

### Task 7: Docs, skill links, GROW closeout

**Files:** `docs/reference/task-graph.md`, pattern, ROUTER, CHANGELOG, series index, agent-coordination deferred links

- [x] **Step 1: Write reference doc + pattern; update indexes**.
- [x] **Step 2: `task qa:prepush` until green**.
- [x] **Step 3: `task gitnexus:analyze`**.
- [ ] **Step 4: Commit** `docs: task graph reference and RFC-0008 closeout` (deferred — ask user).

---

## Out of scope (do not implement in this MR)

RFC-0009–0013, campaign expand, LLM outline expansion, SPA, SQLite.

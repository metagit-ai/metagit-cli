# RFC-0011 Merge Orchestrator & Conflict Resolution — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enqueue and attempt merges of agent branches into integration branches, record conflicts/results, run opt-in validators, and emit merge events — without becoming a hosted CI system.

**Architecture:** New `src/metagit/core/merge/` with models, paths, JSON store, `MergeOrchestrator` service, GitPython merge attempts in temp/worktree-safe flows, conflict records, pluggable validator commands. Thin CLI `metagit merge` + MCP tools. Persistence under `.metagit/merges/`. Events `source=merge`.

**Tech Stack:** GitPython, Pydantic, Click, MCP, pytest with temp git repos.

**Design:** [2026-07-09-rfc-0011-merge-orchestrator-design.md](../specs/2026-07-09-rfc-0011-merge-orchestrator-design.md)  
**Series:** [acl-rfc-series-index](../specs/2026-07-09-acl-rfc-series-index.md)  
**Branch:** `feat/rfc-0010-0011` (same MR as RFC-0010)

## Global constraints

- Modality: CLI + MCP + core + docs/skills; no SPA.
- Persistence: local JSON under session/manifest root `.metagit/merges/`.
- Validators opt-in via appconfig (default empty list).
- Conflict path emits dispatch hints + optional `acl_commands` strings; **no auto-allocate**.
- Never force-push; never bypass remote protections.
- Abort merge cleanly on conflict; do not leave integration branch in a bad recorded state.
- Before editing shared git helpers: impact-analyze; always `task qa:prepush` before hand-off.

## Out of scope

Hosted CI replacement, RFC-0012 scheduler, SPA, force-push, auto ACL allocate for merge agents, SQLite.

## File map (create)

| Path | Responsibility |
|------|----------------|
| `src/metagit/core/merge/__init__.py` | Exports |
| `src/metagit/core/merge/models.py` | MergeRequest, statuses, conflict/validation records, events |
| `src/metagit/core/merge/paths.py` | `.metagit/merges/` + events path |
| `src/metagit/core/merge/store.py` | queue + per-merge JSON with locks |
| `src/metagit/core/merge/service.py` | enqueue/integrate/retry/promote/status |
| `src/metagit/core/merge/validators.py` | Run opt-in shell commands; record results |
| `src/metagit/core/merge/events.py` | Append merge events |
| `src/metagit/core/merge/git_ops.py` | GitPython helpers (ensure branch, merge, abort) |
| `src/metagit/cli/commands/merge_cmd.py` | Click group `merge` (avoid stdlib name clash) |
| `tests/core/merge/` | Unit tests with temp repos |
| `tests/cli/commands/test_merge_cli.py` | CLI tests |
| `tests/core/mcp/test_merge_tools.py` | MCP tests |
| `docs/reference/merge-orchestrator.md` | Operator reference |
| `.mex/patterns/merge-orchestrator.md` | Recurring runbook |

## File map (modify)

- `src/metagit/cli/main.py` — register merge group
- MCP registry/runtime — merge tools
- `event_service.py` — merge `source=merge`
- appconfig models — optional `merge.validators: list[str]` (default `[]`)
- modality-parity, CHANGELOG, ROUTER, series index, agent-coordination link
- skills / agents.md / llms.txt / mkdocs.yml

---

### Task 1: Models + paths + store

**Files:** create `models.py`, `paths.py`, `store.py`, `__init__.py`; tests under `tests/core/merge/`

- [ ] **Step 1: Write failing tests** for MergeRequest validation (slug merge_id, status enum) and store round-trip in temp dir.
- [ ] **Step 2: Run — expect fail**.
- [ ] **Step 3: Implement**

Statuses: `queued | running | succeeded | failed | conflict | validation_failed`

`MergeRequest` fields (minimum):
- `merge_id`, `repository` (project/repo), `source_branch`, `target_branch` (integration/…), `status`
- optional `node_id`, `agent_id`, `conflict`, `validation`, `acl_commands`, timestamps
- `conflict`: `{files: list[str], message: str, dispatch_hint: str | None}`
- `validation`: `{ok: bool, commands: list[{cmd, exit_code, stdout, stderr}]}`

Paths:
- `merges_root` → `.metagit/merges`
- `queue_file` → `queue.json`
- `merge_file(merge_id)` → `<merge_id>.json`
- `events_file` → `.metagit/events/merge.jsonl`

Store: load/save merge docs + queue index (list of merge_ids / lightweight entries). File lock. `T | Exception`.

- [ ] **Step 4: Tests pass**.
- [ ] **Step 5: Commit** `feat(merge): add models and JSON store for RFC-0011`

---

### Task 2: Git ops helpers (temp repo)

**Files:** create `git_ops.py`; test `test_git_ops.py`

- [ ] **Step 1: Failing tests** using a temp git repo (init, two branches, clean merge + conflict case).
- [ ] **Step 2: Implement helpers**
  - `ensure_branch(repo_path, branch, start_point)` — create if missing
  - `attempt_merge(repo_path, source_branch, target_branch) -> MergeGitResult | Exception`
    - checkout target, merge source (`--no-ff` optional; prefer default merge)
    - on conflict: collect unmerged paths, `git merge --abort`, return structured conflict (do not leave merge in progress)
    - on success: return new commit sha
  - Never push.
- [ ] **Step 3: Tests pass**.
- [ ] **Step 4: Commit** `feat(merge): GitPython merge attempt with clean abort`

---

### Task 3: Enqueue + integrate service

**Files:** create `service.py`, `events.py`; test `test_service_integrate.py`

- [ ] **Step 1: Failing tests**
  - enqueue creates queued MergeRequest
  - integrate clean branch → succeeded + event MergeSucceeded
  - integrate conflicting branch → conflict status + ConflictDetected; target branch HEAD unchanged / not left mid-merge
- [ ] **Step 2: Implement `MergeOrchestrator`**
  - `enqueue(repository, source_branch, target_branch, *, node_id=None, agent_id=None, repo_path=...)`
  - Resolve `repo_path` from workspace sync root + project/repo when possible; allow explicit path in tests
  - `integrate(merge_id)` — set running, call git_ops, persist result, emit events
  - `retry(merge_id)` — re-queue failed/conflict and integrate again (or set queued then integrate)
  - `status(repository=None)` — list merges
  - On conflict: fill `acl_commands` hint strings only (allocate/lease/worktree/claim) — no git mutations for ACL
- [ ] **Step 3: Tests pass**.
- [ ] **Step 4: Commit** `feat(merge): enqueue and integrate with conflict records`

---

### Task 4: Validators + promote gate

**Files:** create `validators.py`; extend service; test `test_validators.py`

- [ ] **Step 1: Failing tests**
  - empty validators → validation ok
  - failing command → `validation_failed`, blocks promote
  - promote succeeds only when status succeeded and validation ok (or validators empty)
- [ ] **Step 2: Implement**
  - Read validators from appconfig path if available; default `[]`
  - `run_validators(repo_path, commands) -> ValidationResult`
  - `promote(merge_id, into_branch)` — merge integration → feature only if status succeeded and validation ok; else return error
- [ ] **Step 3: Tests pass**.
- [ ] **Step 4: Commit** `feat(merge): opt-in validators and gated promote`

---

### Task 5: Events feed merge

**Files:** modify `event_service.py`; test merge events visible with `source=merge`

- [ ] **Step 1: Wire MergeEventStore into WorkspaceEventService** (mirror semantic/taskgraph).
- [ ] **Step 2: Test + commit** `feat(merge): emit merge events into context feed`

---

### Task 6: CLI `metagit merge`

**Files:** `merge_cmd.py`, `main.py`, `test_merge_cli.py`

Commands:
- `enqueue --repository --branch --into [--node-id] [--repo-path] [--json]`
- `status [--repository] [--json]`
- `integrate --merge-id [--json]`
- `retry --merge-id [--json]`
- `promote --merge-id --into [--json]`

Reuse acl_common roots. For tests, pass `--repo-path` to temp git repo.

- [ ] Commit `feat(cli): add metagit merge commands`

---

### Task 7: MCP + modality parity

Tools: `metagit_merge_enqueue`, `metagit_merge_status`, `metagit_merge_retry`, `metagit_merge_integrate` (promote optional).

Feature id: `merge_orchestrator`.

- [ ] Commit `feat(mcp): add merge orchestrator tools and modality parity`

---

### Task 8: Docs + GROW + QA

- Create `docs/reference/merge-orchestrator.md`
- Link from agent-coordination
- Pattern + INDEX
- CHANGELOG, ROUTER, series index (0011 Implemented on branch)
- `task qa:prepush` + `task gitnexus:analyze`
- Commit `docs: merge orchestrator reference and RFC-0011 closeout`

---

## Acceptance checklist

- [ ] Clean merge succeeds in temp repo test.
- [ ] Conflict produces record without leaving integration mid-merge.
- [ ] Validators opt-in default empty; failure blocks promote.
- [ ] Events `source=merge`; modality registered; docs published.
- [ ] `task qa:prepush` green.

## Decisions (locked)

1. Validators default empty (opt-in via config).
2. No auto ACL allocate; hints only.
3. Agent→integration is MVP; promote is explicit gated step.
4. GitNexus import unrelated — stay out of this RFC.

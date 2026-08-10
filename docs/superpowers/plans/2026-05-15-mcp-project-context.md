# MCP Project Context & Snapshot — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add MCP tools and core services so agents can switch workspace project context with persisted session state and create/restore workspace git-state snapshots.

**Architecture:** Pydantic models in `core/workspace/context_models.py`; `SessionStore` writes under `.metagit/sessions/`; `ProjectContextService` and `WorkspaceSnapshotService` orchestrate index + repo inspect; MCP runtime registers three tools (+ optional `metagit_session_update`). CLI parity is a follow-up task group.

**Tech stack:** Python 3.x, Pydantic, GitPython, existing MCP runtime (`MetagitMcpRuntime`), pytest.

**Design spec:** `docs/superpowers/specs/2026-05-15-mcp-project-context-design.md`

---

## File map

| File | Responsibility |
|------|----------------|
| `src/metagit/core/workspace/context_models.py` | `ProjectSession`, `WorkspaceSnapshot`, bundles |
| `src/metagit/core/mcp/services/session_store.py` | JSON persistence under `.metagit/` |
| `src/metagit/core/mcp/services/project_context.py` | Switch + env resolution |
| `src/metagit/core/mcp/services/workspace_snapshot.py` | Create/restore snapshots |
| `src/metagit/core/mcp/runtime.py` | Schemas + dispatch |
| `src/metagit/core/mcp/tool_registry.py` | Tool names |
| `tests/core/mcp/services/test_session_store.py` | Store unit tests |
| `tests/core/mcp/services/test_project_context.py` | Context service tests |
| `tests/core/mcp/services/test_workspace_snapshot.py` | Snapshot tests |
| `tests/core/mcp/test_runtime.py` | MCP list/call/invalid args |
| `tests/fixtures/workspace_multi_project/` | Fixture `.metagit.yml` + dirs |

---

### Task 1: Context models

**Files:**
- Create: `src/metagit/core/workspace/context_models.py`
- Test: `tests/core/workspace/test_context_models.py`

- [ ] **Step 1:** Write failing tests for model validation (`env_overrides` key regex, `agent_notes` max length).
- [ ] **Step 2:** Implement Pydantic models from spec.
- [ ] **Step 3:** Run `uv run pytest tests/core/workspace/test_context_models.py -q`

---

### Task 2: SessionStore

**Files:**
- Create: `src/metagit/core/mcp/services/session_store.py`
- Test: `tests/core/mcp/services/test_session_store.py`

- [ ] **Step 1:** Failing tests — read missing file returns defaults; write/read roundtrip; corrupt JSON returns empty session.
- [ ] **Step 2:** Implement `get_workspace_meta`, `set_active_project`, `get_project_session`, `update_project_session`.
- [ ] **Step 3:** Test secret heuristic rejection on `env_overrides` values.
- [ ] **Step 4:** `uv run pytest tests/core/mcp/services/test_session_store.py -q`

---

### Task 3: ProjectContextService

**Files:**
- Create: `src/metagit/core/mcp/services/project_context.py`
- Test: `tests/core/mcp/services/test_project_context.py`
- Reuse: `WorkspaceIndexService`, `RepoOperationsService`

- [ ] **Step 1:** Fixture `tests/fixtures/workspace_multi_project/.metagit.yml` with projects `alpha` and `beta`, two repos each (use `git init` in test setup).
- [ ] **Step 2:** Failing test — switch to valid project returns repos and sets active project in store.
- [ ] **Step 3:** Failing test — unknown project returns `ok: false`.
- [ ] **Step 4:** Implement `switch()` with `restore_session`, `setup_env`, inspect cap 20.
- [ ] **Step 5:** Test env export includes `METAGIT_PROJECT` and excludes secret kinds.
- [ ] **Step 6:** `uv run pytest tests/core/mcp/services/test_project_context.py -q`

---

### Task 4: WorkspaceSnapshotService

**Files:**
- Create: `src/metagit/core/mcp/services/workspace_snapshot.py`
- Test: `tests/core/mcp/services/test_workspace_snapshot.py`

- [ ] **Step 1:** Failing test — `create` writes file under `.metagit/snapshots/`.
- [ ] **Step 2:** Failing test — `restore` loads snapshot and calls context switch when `switch_project=true`.
- [ ] **Step 3:** Implement create/restore; document no git mutation in restore response `notes`.
- [ ] **Step 4:** `uv run pytest tests/core/mcp/services/test_workspace_snapshot.py -q`

---

### Task 5: MCP runtime wiring

**Files:**
- Modify: `src/metagit/core/mcp/runtime.py`
- Modify: `src/metagit/core/mcp/tool_registry.py`
- Test: `tests/core/mcp/test_runtime.py`

- [ ] **Step 1:** Add tool schemas: `metagit_project_context_switch`, `metagit_workspace_state_snapshot`, `metagit_workspace_state_restore`, `metagit_session_update`.
- [ ] **Step 2:** Register in `_active_tools`.
- [ ] **Step 3:** Dispatch branches calling services; map validation errors to `InvalidToolArgumentsError`.
- [ ] **Step 4:** Extend `test_runtime.py` — tools visible when active; call switch with fixture root; invalid project returns structured error.
- [ ] **Step 5:** `uv run pytest tests/core/mcp/test_runtime.py -q`

---

### Task 6: Documentation and skills

**Files:**
- Modify: `docs/cli_reference.md` (MCP tool section)
- Modify: `CHANGELOG.md`
- Modify: `skills/metagit-workspace-scope/SKILL.md`
- Modify: `skills/metagit-control-center/SKILL.md`
- Modify: `src/metagit/data/skills/*` (sync via `task skills:sync`)

- [ ] **Step 1:** Document tools, session paths, agent contract, restore limitations.
- [ ] **Step 2:** Add CHANGELOG entry under Unreleased.
- [ ] **Step 3:** Run `task skills:sync generate:schema`.

---

### Task 7: Scaffold updates (session closeout)

- [ ] Update `.mex/context/mcp-runtime.md` with new services/tools.
- [ ] Add `.mex/patterns/mcp-project-context.md` if workflow is non-obvious.
- [ ] Update `.mex/ROUTER.md` Current Project State.
- [ ] Run `task qa:prepush`.

---

### Task 8 (optional v1.1): CLI

**Files:**
- Create: `src/metagit/cli/commands/workspace_context.py`
- Modify: `src/metagit/cli/commands/workspace.py`

- [ ] `metagit workspace context switch|show|snapshot create|snapshot restore --json`

---

## Dependency order

```
Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7
                              ↘ optional Task 8
```

## Out of scope for this plan

- Phase 1 search/sync improvements
- `metagit_cross_project_dependencies`
- MCP resource URI for context polling (noted in spec v0.3)

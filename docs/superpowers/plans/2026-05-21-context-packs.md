# Context Packs and Repo Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship T0 workspace map and T1 repo cards via `metagit context pack` CLI and MCP tools, composing existing catalog/index/git-stats services.

**Architecture:** New `src/metagit/core/context/` package with Pydantic models and three services (`WorkspaceMapService`, `RepoCardService`, `ContextPackService`). Thin CLI group and MCP dispatch branches return JSON via `model_dump(mode="json")`.

**Tech Stack:** Python 3.12+, Pydantic, Click CLI, existing MCP runtime.

**Spec:** `docs/superpowers/specs/2026-05-21-context-packs-design.md`

---

### Task 1: Context models

**Files:**
- Create: `src/metagit/core/context/__init__.py`
- Create: `src/metagit/core/context/models.py`
- Test: `tests/core/context/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
from metagit.core.context.models import ContextPackResult, RepoCardResult, WorkspaceMapResult


def test_workspace_map_result_defaults():
    result = WorkspaceMapResult(workspace_name="demo")
    assert result.tier == 0
    assert result.workspace_name == "demo"
    assert result.repos == []


def test_repo_card_result_tier():
    card = RepoCardResult(project_name="p", repo_name="r", repo_path="/tmp/r")
    assert card.tier == 1
    assert card.health_flags == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/core/context/test_models.py -v`  
Expected: FAIL (module not found)

- [ ] **Step 3: Write minimal implementation**

Create models per spec: `WorkspaceMapEntry`, `WorkspaceMapResult`, `RepoCardResult`, `ContextPackResult` with `tier` literals, optional fields, `health_flags`, `stack_hints`, `token_estimate`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/core/context/test_models.py -v`  
Expected: PASS

---

### Task 2: WorkspaceMapService (T0)

**Files:**
- Create: `src/metagit/core/context/workspace_map_service.py`
- Test: `tests/core/context/test_workspace_map_service.py`

- [ ] **Step 1: Write failing test** using temp dir + minimal `MetagitConfig` with one project/repo (copy pattern from `tests/core/mcp/services/test_project_context.py`).

- [ ] **Step 2: Run test — expect FAIL**

- [ ] **Step 3: Implement `WorkspaceMapService.build`** delegating to `WorkspaceCatalogService.list_workspace`. Map index rows to `WorkspaceMapEntry`. Accept optional `active_project` string.

- [ ] **Step 4: Run test — expect PASS**

---

### Task 3: RepoCardService (T1)

**Files:**
- Create: `src/metagit/core/context/repo_card_service.py`
- Test: `tests/core/context/test_repo_card_service.py`

- [ ] **Step 1: Write failing tests:**
  - existing git repo → branch populated, stack hint for `pyproject.toml` if present
  - missing clone path → `exists=False`, `health_flags` contains `missing_clone`
  - `stale_head_30d` flag when head age > 30

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement service:**
  - `_stack_hints(repo_path)` — check fixed list: `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `Dockerfile`, `Taskfile.yml`, `Makefile`, `README.md`
  - `_health_flags(...)` from index + inspect dict
  - `_instruction_excerpt(config, project, repo)` — truncate composed instructions to 500 chars
  - `build_one`, `build_many(max_cards=50)`

- [ ] **Step 4: Run tests — expect PASS**

---

### Task 4: ContextPackService

**Files:**
- Create: `src/metagit/core/context/context_pack_service.py`
- Test: `tests/core/context/test_context_pack_service.py`

- [ ] **Step 1: Write failing tests for tier 0 and tier 1 with project filter**

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement orchestrator** with `_estimate_tokens(payload)` ≈ len(json.dumps)/4

- [ ] **Step 4: Run — PASS**

---

### Task 5: CLI commands

**Files:**
- Create: `src/metagit/cli/commands/context.py`
- Modify: `src/metagit/cli/main.py` (register `context` group)
- Test: `tests/cli/commands/test_context.py`

- [ ] **Step 1: Write failing CLI test** using CliRunner: `metagit context pack --tier 0 --json` in temp workspace

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement commands** `pack` and `repo-card`; load config via `MetagitConfigManager`; respect `METAGIT_AGENT_MODE` / `--json`

- [ ] **Step 4: Run — PASS**

---

### Task 6: MCP tools

**Files:**
- Modify: `src/metagit/core/mcp/tool_registry.py`
- Modify: `src/metagit/core/mcp/runtime.py`
- Test: `tests/core/mcp/test_runtime.py`

- [ ] **Step 1: Add failing tests** for `metagit_context_pack` and `metagit_repo_card` in tools/list (ACTIVE) and tools/call

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Add schemas + dispatch** following `.mex/patterns/add-mcp-tool.md`

- [ ] **Step 4: Run MCP tests — PASS**

---

### Task 7: Prompt catalog entry

**Files:**
- Modify: `src/metagit/core/prompt/models.py` (add `context-pack` to PromptKind)
- Modify: `src/metagit/core/prompt/catalog.py`
- Test: `tests/core/prompt/test_prompt_service.py`

- [ ] **Step 1: Failing test** — `context-pack` listed for workspace scope

- [ ] **Step 2–4: Implement template body** referencing tier 0/1 usage

---

### Task 8: QA and scaffold updates

**Files:**
- Modify: `.mex/ROUTER.md` (add context packs to Working)
- Optional: `docs/reference/context-packs.md` one-pager

- [ ] Run `task qa:prepush` — must pass

---

## Execution order

Tasks 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 (sequential; each builds on prior)

# ADHD-Friendly Resume Status Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add low-friction objective note capture plus a one-command resume flow that reliably surfaces the best current objective and portable repo paths.

**Architecture:** Extend the existing objective/context stack instead of introducing a parallel state system. Keep business logic in `ObjectiveService` (normalization, ranking, and note synthesis), then expose thin adapters in CLI and MCP; update docs and parity registry to preserve modality discipline.

**Tech Stack:** Python 3.12+, Click CLI, Pydantic models, pytest, MCP runtime schemas.

## Global Constraints

- Preserve backward compatibility for existing objective JSON envelopes and CLI usage patterns.
- Keep Click handlers thin; put durable behavior in core services.
- Normalize objective repo references to workspace-relative paths only when safely inside the workspace root.
- Do not duplicate business logic across CLI and MCP; share service methods.
- Add/adjust tests for every touched behavior path.

---

### Task 1: Add Objective Ergonomic Capture + Path Normalization Core

**Files:**
- Modify: `src/metagit/core/context/objective_service.py`
- Test: `tests/core/context/test_objective_service.py`

**Interfaces:**
- Consumes: `ObjectiveService.upsert_partial(partial: dict[str, Any]) -> Objective`
- Produces:
  - `ObjectiveService.upsert_partial(...)` supports optional synthesized notes input keys
  - `ObjectiveService.edit(objective_id: str, updates: dict[str, Any]) -> Objective` path normalization behavior
  - New helper(s), internal only, for repo path normalization and note synthesis

- [ ] **Step 1: Write failing unit tests for new behavior**

```python
# tests/core/context/test_objective_service.py
# Add tests for:
# 1) repos normalize to ./relative/path when inside workspace root
# 2) repos remain absolute when outside workspace root
# 3) synthetic note fields (left_off/next/blockers) become human_notes
```

- [ ] **Step 2: Run focused tests to verify failures**

Run: `pytest tests/core/context/test_objective_service.py -q`
Expected: FAIL for missing normalization/synthesis behavior.

- [ ] **Step 3: Implement minimal core logic in ObjectiveService**

```python
# src/metagit/core/context/objective_service.py
# 1) add _normalize_repo_refs(repos, workspace_root)
# 2) add _compose_human_notes(data)
# 3) call normalization + compose logic in upsert_partial/edit
```

- [ ] **Step 4: Re-run focused service tests**

Run: `pytest tests/core/context/test_objective_service.py -q`
Expected: PASS for new and existing objective service tests.

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/context/objective_service.py tests/core/context/test_objective_service.py
git commit -m "feat(context): normalize objective repos and synthesize human notes"
```

### Task 2: CLI Enhancements for Objective Set/Edit and Resume/Pause

**Files:**
- Modify: `src/metagit/cli/commands/context.py`
- Test: `tests/cli/commands/test_context.py`

**Interfaces:**
- Consumes: `ObjectiveService.upsert_partial(...)`, `ObjectiveService.edit(...)`, new resume selection method
- Produces:
  - `metagit context objective set` supports `--human-notes`, `--left-off`, `--next`, `--blockers`, `--notes-file`
  - `metagit context objective edit` new subcommand
  - `metagit context resume [filter]` new command
  - `metagit context pause` helper command

- [ ] **Step 1: Add failing CLI tests first**

```python
# tests/cli/commands/test_context.py
# Add tests covering:
# - objective set with --human-notes
# - objective set with --left-off/--next/--blockers
# - objective edit updates human_notes
# - context resume selects latest in_progress objective
# - context resume with filter matches title/repo/notes
# - context pause creates/upserts objective with status=in_progress
```

- [ ] **Step 2: Run focused CLI tests for expected failure**

Run: `pytest tests/cli/commands/test_context.py -q`
Expected: FAIL for missing commands/options.

- [ ] **Step 3: Implement CLI command extensions**

```python
# src/metagit/cli/commands/context.py
# extend objective_set_cmd options + merge helper
# add objective_edit_cmd
# add context resume and pause command handlers
```

- [ ] **Step 4: Re-run focused CLI tests**

Run: `pytest tests/cli/commands/test_context.py -q`
Expected: PASS for new and existing context CLI tests.

- [ ] **Step 5: Commit**

```bash
git add src/metagit/cli/commands/context.py tests/cli/commands/test_context.py
git commit -m "feat(context): add ADHD-friendly objective capture and resume CLI"
```

### Task 3: MCP Parity for Resume + Objective Edit Payload

**Files:**
- Modify: `src/metagit/core/mcp/runtime.py`
- Test: `tests/core/mcp/test_runtime.py`

**Interfaces:**
- Consumes: objective service resume selection and edit behavior
- Produces:
  - `metagit_context_resume` tool schema/dispatch
  - `metagit_objective_edit` accepts parity note fields where appropriate

- [ ] **Step 1: Add failing MCP runtime tests**

```python
# tests/core/mcp/test_runtime.py
# Add tests for:
# - metagit_context_resume tool in tool list and successful call
# - objective edit parity fields accepted and persisted
```

- [ ] **Step 2: Run targeted MCP tests to verify failure**

Run: `pytest tests/core/mcp/test_runtime.py -q -k "objective or resume"`
Expected: FAIL due to missing schema/dispatch.

- [ ] **Step 3: Implement runtime schema + dispatch**

```python
# src/metagit/core/mcp/runtime.py
# add schema entry for metagit_context_resume
# wire dispatch branch calling ObjectiveService resume selector
```

- [ ] **Step 4: Re-run targeted MCP tests**

Run: `pytest tests/core/mcp/test_runtime.py -q -k "objective or resume"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/mcp/runtime.py tests/core/mcp/test_runtime.py
git commit -m "feat(mcp): add context resume parity tooling"
```

### Task 4: Documentation + Modality Registry + Final Verification

**Files:**
- Modify: `docs/agents.md`
- Modify: `docs/reference/context-switch.md` (or split into `context-resume.md` if warranted)
- Modify: `src/metagit/data/skills/metagit-context-pack/SKILL.md`
- Modify: `scripts/modality-parity.yml`
- Modify (generated): `docs/reference/modality-feature-registry.md`

**Interfaces:**
- Consumes: implemented CLI and MCP behaviors
- Produces: updated agent workflows and parity declaration

- [ ] **Step 1: Update docs and skill references**

```markdown
# Document one-command pause/resume flow with examples,
# and objective set/edit ergonomic flags.
```

- [ ] **Step 2: Update parity registry source and regenerate docs**

Run: `task generate:modality-registry`
Expected: modality registry includes resume tracking feature row.

- [ ] **Step 3: Run focused tests for touched surfaces**

Run: `pytest tests/core/context/test_objective_service.py tests/cli/commands/test_context.py tests/core/mcp/test_runtime.py -q`
Expected: PASS.

- [ ] **Step 4: Run full quality gate**

Run: `task qa:prepush`
Expected: PASS.

- [ ] **Step 5: Run final GitNexus analyze gate**

Run: `task gitnexus:analyze`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add docs/agents.md docs/reference/context-switch.md src/metagit/data/skills/metagit-context-pack/SKILL.md scripts/modality-parity.yml docs/reference/modality-feature-registry.md
git commit -m "docs: document resume workflow and register modality parity"
```

## Spec Coverage Self-Check

- Objective capture ergonomics: covered in Task 2 (`objective set` flags, pause helper).
- ADHD-friendly resume command: covered in Task 2 + Task 3 parity.
- Relative path portability: covered in Task 1 service normalization.
- Workflow examples and adoption docs: covered in Task 4.
- Cross-modality coherence: covered in Task 3 + Task 4 registry updates.

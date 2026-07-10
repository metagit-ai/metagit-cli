# RFC-0013 Agent Operating System (Composition) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a thin composition façade (`metagit aos|coord status|doctor|next` + MCP + skill) that aggregates ACL, task graph, and any present 0009–0012 subsystems into one operator snapshot and a preview/commit “what next” envelope — without new engines or AOS persistence.

**Architecture:** `src/metagit/core/aos/` orchestrates existing services behind Protocol collectors. Status/doctor are read-mostly; doctor `--fix --yes` calls ACL lease expire-on-list + `WorktreeService.gc()` only; `next` preview uses scheduler dry-run (or pure scoring), `--commit` calls `SchedulerService.next()`, `--apply-hints` calls coordination APIs (never models, never compile execution).

**Tech Stack:** Pydantic, Click, MCP, pytest with injectable collectors/fakes.

**Design:** [2026-07-09-rfc-0013-aos-composition-design.md](../specs/2026-07-09-rfc-0013-aos-composition-design.md)  
**Series:** [acl-rfc-series-index](../specs/2026-07-09-acl-rfc-series-index.md)  
**Branch:** `feat/rfc-0013-aos` (worktree `.worktrees/rfc-0013`)

## Locked decisions

1. **Naming:** CLI/MCP primary `aos`; alias `coord` / `metagit_coord_*`.
2. **Doctor:** report-only by default; `--fix --yes` (MCP `fix`+`confirm`) for safe ACL GC only.
3. **Skills:** new `metagit-aos` + pointer from `metagit-agent-coordination`.
4. **Surface:** `status` + `doctor` + `next` (no `aos run` executor).
5. **`next` recording:** preview by default; `--commit` records via scheduler.
6. **`--apply-hints`:** ACL bind APIs only; never launches models; compile is hint-only.
7. **Architecture:** thin aggregator; no AOS persistence; no snapshot cache.
8. **Modality:** `aos_status` only.
9. **GitNexus:** use CLI (`task gitnexus:analyze` / impact) when MCP LadybugDB is version-mismatched.

## Global constraints

- Modality: CLI + MCP + core + docs/skills; no SPA; no `/v3/ops`.
- No new persistence under `.metagit/aos/`.
- Composition only — no new task/merge/schedule/semantic engines.
- Hard floor for useful status/next: RFC-0007 + RFC-0008; 0009–0012 soft.
- Before editing shared symbols: GitNexus impact (CLI if MCP broken); always `task qa:prepush` before hand-off.
- Implement on feature branch / worktree, not `main`.

## Out of scope

New engines, AOS snapshot cache, `aos run` chain executor, SPA, SQLite, launching models, doctor claim/merge/task mutations, replacing control-center/campaigns.

## File map (create)

| Path | Responsibility |
|------|----------------|
| `src/metagit/core/aos/__init__.py` | Exports |
| `src/metagit/core/aos/models.py` | Snapshot, doctor, next envelopes + finding models |
| `src/metagit/core/aos/protocols.py` | Collector Protocols for subsystems |
| `src/metagit/core/aos/collectors.py` | Default collectors wrapping real services (try/import degrade) |
| `src/metagit/core/aos/service.py` | `AosService.status` / `doctor` / `next` |
| `src/metagit/core/aos/hints.py` | Build compile/ACL hint strings; apply ACL binds via coordination services |
| `src/metagit/cli/commands/aos.py` | Click group `aos` (registered also as `coord`) |
| `tests/core/aos/test_models.py` | Model defaults / validation |
| `tests/core/aos/test_service_status.py` | Status aggregation + degrade |
| `tests/core/aos/test_service_doctor.py` | Doctor findings + fix gating |
| `tests/core/aos/test_service_next.py` | Preview vs commit vs apply-hints |
| `tests/cli/commands/test_aos_cli.py` | CLI + `coord` alias |
| `tests/core/mcp/test_aos_tools.py` | MCP primary + alias tools |
| `docs/reference/aos.md` | Operator reference (ship with implementation) |
| `skills/metagit-aos/SKILL.md` | Bundled skill (sync to packaged copies via `task skills:sync`) |
| `.mex/patterns/aos-composition.md` | Recurring runbook |

## File map (modify)

| Path | Change |
|------|--------|
| `src/metagit/core/scheduler/service.py` | Add `preview_next(...)` (score + build decisions **without** persist/events) |
| `src/metagit/cli/main.py` | Register `aos_group` and alias `coord` |
| `src/metagit/core/mcp/tool_registry.py` | Register `metagit_aos_*` + `metagit_coord_*` |
| `src/metagit/core/mcp/runtime.py` | Tool schemas + handlers (aliases share handlers) |
| `scripts/modality-parity.yml` | Feature `aos_status` |
| `skills/metagit-agent-coordination/SKILL.md` (+ packaged mirrors via sync) | Short AOS pointer + modality marker |
| `docs/reference/agent-coordination.md` | Link to AOS |
| `docs/agents.md`, `AGENTS.md`, `llms.txt`, `mkdocs.yml` | Index links |
| `CHANGELOG.md` | feat entry |
| `.mex/ROUTER.md` | Project state |
| Series index | Mark Implemented when shipped |

## Scheduler preview contract (Task 2)

Add to `SchedulerService`:

```python
def preview_next(
    self, graph_id: str | None = None, *, limit: int = 1
) -> list[ScheduleDecision] | Exception:
    """Same ranking as next(), but do not append decisions.jsonl or emit events."""
```

Reuse existing scoring / `_build_decision` path; skip `_persist_decision`. Decision IDs may still be generated for the envelope (ephemeral).

---

### Task 0: Branch / worktree

**Files:** none (git only)

- [ ] **Step 1: Create worktree + branch from current base (prefer `main` with 0008–0012 available)**

```bash
git fetch origin
git worktree add -b feat/rfc-0013-aos .worktrees/rfc-0013 main
cd .worktrees/rfc-0013
```

If RFC-0012 is not yet on `main`, branch from `feat/rfc-0012-agent-scheduler` (or merge it) so scheduler APIs exist.

- [ ] **Step 2: Confirm clean tree**

```bash
git status
```

Expected: on `feat/rfc-0013-aos`, clean (or only intentional carry-overs).

---

### Task 1: AOS models

**Files:**
- Create: `src/metagit/core/aos/__init__.py`, `src/metagit/core/aos/models.py`
- Test: `tests/core/aos/test_models.py`

- [ ] **Step 1: Write failing tests**

```python
#!/usr/bin/env python
"""Tests for AOS composition models."""

from metagit.core.aos.models import (
    AosDoctorResult,
    AosFinding,
    AosNextResult,
    AosStatusResult,
    AosSubsystemSection,
)


def test_subsystem_section_defaults() -> None:
    section = AosSubsystemSection(available=False)
    assert section.available is False
    assert section.summary == {}


def test_status_result_requires_generated_at() -> None:
    result = AosStatusResult(
        generated_at="2026-07-09T00:00:00Z",
        subsystems={
            "acl": AosSubsystemSection(available=True, summary={"leases_active": 0}),
            "taskgraph": AosSubsystemSection(available=True, summary={"ready": 0}),
        },
    )
    assert "acl" in result.subsystems
    assert result.subsystems["taskgraph"].available is True


def test_doctor_finding_and_next_flags() -> None:
    finding = AosFinding(
        severity="warning",
        code="stale_lease",
        message="lease expired",
        subsystem="acl",
    )
    doctor = AosDoctorResult(
        generated_at="2026-07-09T00:00:00Z",
        subsystems={},
        findings=[finding],
        suggested_commands=["metagit worktree gc"],
        fixed=[],
    )
    assert doctor.findings[0].code == "stale_lease"
    nxt = AosNextResult(
        generated_at="2026-07-09T00:00:00Z",
        committed=False,
        hints_applied=False,
        scheduler_available=True,
    )
    assert nxt.decision is None
    assert nxt.acl_commands == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/core/aos/test_models.py -v
```

Expected: FAIL (module not found).

- [ ] **Step 3: Implement models**

`src/metagit/core/aos/models.py`:

```python
#!/usr/bin/env python
"""Pydantic envelopes for AOS composition (RFC-0013)."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

FindingSeverity = Literal["info", "warning", "error"]


class AosSubsystemSection(BaseModel):
    available: bool
    summary: dict[str, Any] = Field(default_factory=dict)


class AosStatusResult(BaseModel):
    generated_at: str
    subsystems: dict[str, AosSubsystemSection] = Field(default_factory=dict)


class AosFinding(BaseModel):
    severity: FindingSeverity
    code: str
    message: str
    subsystem: str


class AosDoctorResult(AosStatusResult):
    findings: list[AosFinding] = Field(default_factory=list)
    suggested_commands: list[str] = Field(default_factory=list)
    fixed: list[str] = Field(default_factory=list)


class AosNextResult(BaseModel):
    generated_at: str
    decision: Optional[dict[str, Any]] = None
    compile_command: Optional[str] = None
    acl_commands: list[str] = Field(default_factory=list)
    committed: bool = False
    hints_applied: bool = False
    scheduler_available: bool = False
    reasons: list[str] = Field(default_factory=list)
```

`__init__.py` exports the public models + (later) `AosService`.

- [ ] **Step 4: Run tests — expect PASS**

```bash
uv run pytest tests/core/aos/test_models.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/metagit/core/aos/__init__.py src/metagit/core/aos/models.py tests/core/aos/test_models.py
git commit -m "$(cat <<'EOF'
feat(aos): add RFC-0013 composition envelope models

EOF
)"
```

---

### Task 2: Scheduler `preview_next` (shared hook)

**Files:**
- Modify: `src/metagit/core/scheduler/service.py`
- Test: `tests/core/scheduler/test_preview_next.py`

- [ ] **Step 1: Write failing test**

```python
#!/usr/bin/env python
"""preview_next must not persist decisions."""

from pathlib import Path

from metagit.core.scheduler.service import SchedulerService
from metagit.core.taskgraph.models import TaskNode
from metagit.core.taskgraph.service import TaskGraphService


def test_preview_next_does_not_append_decisions(tmp_path: Path) -> None:
    root = str(tmp_path)
    tasks = TaskGraphService(root)
    graph = tasks.create(title="g", objective_id=None)
    assert not isinstance(graph, Exception)
    # create one ready node via expand or direct store — match existing scheduler tests
    ready_nodes = [
        TaskNode(
            node_id="n1",
            graph_id=graph.graph_id,
            title="t",
            status="ready",
            priority=5,
            project="p",
            repository="p/r",
        )
    ]

    def ready_fn(_gid: str | None) -> list[TaskNode]:
        return ready_nodes

    svc = SchedulerService(root, ready_fn=ready_fn, worktrees_fn=lambda: [], merge_status_fn=lambda: [])
    preview = svc.preview_next(limit=1)
    assert not isinstance(preview, Exception)
    assert len(preview) == 1
    listed = svc.store.list_decisions()
    assert not isinstance(listed, Exception)
    assert listed == []

    committed = svc.next(limit=1)
    assert not isinstance(committed, Exception)
    listed2 = svc.store.list_decisions()
    assert not isinstance(listed2, Exception)
    assert len(listed2) == 1
```

Adapt node construction to match how other scheduler tests seed ready nodes (copy patterns from `tests/core/scheduler/test_service.py`).

- [ ] **Step 2: Run — expect FAIL** (`preview_next` missing).

- [ ] **Step 3: Implement `preview_next`** by extracting shared `_rank_ready(...)` used by both `next` and `preview_next`; only `next` calls `_persist_decision`.

- [ ] **Step 4: Tests pass** (new + existing scheduler suite).

```bash
uv run pytest tests/core/scheduler/ -v
```

- [ ] **Step 5: Commit** `feat(scheduler): add preview_next without persisting decisions`

---

### Task 3: Protocols + collectors + status

**Files:**
- Create: `protocols.py`, `collectors.py`, `service.py` (status method)
- Test: `tests/core/aos/test_service_status.py`

- [ ] **Step 1: Write failing tests**

```python
#!/usr/bin/env python
"""AosService.status aggregation and degrade behavior."""

from metagit.core.aos.models import AosSubsystemSection
from metagit.core.aos.service import AosService


class FakeCollectors:
    def __init__(self, sections: dict[str, AosSubsystemSection]) -> None:
        self._sections = sections

    def collect_all(self) -> dict[str, AosSubsystemSection]:
        return self._sections


def test_status_includes_only_provided_sections(tmp_path) -> None:
    sections = {
        "acl": AosSubsystemSection(available=True, summary={"leases_active": 1}),
        "taskgraph": AosSubsystemSection(available=True, summary={"ready": 2, "blocked": 1}),
        "scheduler": AosSubsystemSection(available=False),
    }
    svc = AosService(str(tmp_path), collectors=FakeCollectors(sections))
    result = svc.status()
    assert not isinstance(result, Exception)
    assert result.subsystems["acl"].summary["leases_active"] == 1
    assert result.subsystems["scheduler"].available is False


def test_status_works_with_acl_and_taskgraph_only(tmp_path) -> None:
    sections = {
        "acl": AosSubsystemSection(available=True, summary={}),
        "taskgraph": AosSubsystemSection(available=True, summary={"ready": 0}),
        "context_compile": AosSubsystemSection(available=False),
        "semantic": AosSubsystemSection(available=False),
        "merge": AosSubsystemSection(available=False),
        "scheduler": AosSubsystemSection(available=False),
    }
    svc = AosService(str(tmp_path), collectors=FakeCollectors(sections))
    result = svc.status()
    assert not isinstance(result, Exception)
    assert result.subsystems["taskgraph"].available is True
```

- [ ] **Step 2: Run — expect FAIL**.

- [ ] **Step 3: Implement**

`protocols.py` — `SubsystemCollector` Protocol with `collect_all() -> dict[str, AosSubsystemSection]`.

`collectors.py` — `DefaultSubsystemCollector(session_root)`:

| Key | Source |
|-----|--------|
| `acl` | `LeaseService.list()`, `WorktreeService.list()`, `ClaimService.list()` → counts |
| `taskgraph` | `TaskGraphService.list` / ready + count by status |
| `context_compile` | `available=True` if `metagit.core.context.compiler` importable; summary may be empty (do **not** run compile) |
| `semantic` | try `SemanticService`; conflict count best-effort (skip or `0` if repo-scoped API needs a repo — prefer `available=True` + `concepts` count from store if cheap) |
| `merge` | `MergeOrchestrator.status()` → counts by status |
| `scheduler` | `SchedulerService.status()` → `ready_count`, recent decision ids |

On import/runtime errors: section `available=False`, `summary={"error": "..."}` optional but keep messages short.

`AosService.status()` → `AosStatusResult(generated_at=..., subsystems=collector.collect_all())`.

- [ ] **Step 4: Tests pass**.

- [ ] **Step 5: Commit** `feat(aos): status aggregation with soft subsystem collectors`

---

### Task 4: Doctor (report + gated fix)

**Files:**
- Extend: `service.py`, optionally `collectors.py`
- Test: `tests/core/aos/test_service_doctor.py`

- [ ] **Step 1: Write failing tests**

```python
#!/usr/bin/env python
"""Doctor findings and --fix gating."""

from metagit.core.aos.models import AosSubsystemSection
from metagit.core.aos.service import AosService


class FakeCollectors:
    def __init__(self) -> None:
        self.sections = {
            "acl": AosSubsystemSection(
                available=True,
                summary={"leases_expired": 1, "worktrees_active": 1},
            ),
            "taskgraph": AosSubsystemSection(
                available=True,
                summary={"ready": 0, "blocked": 2},
            ),
            "scheduler": AosSubsystemSection(available=False),
            "context_compile": AosSubsystemSection(available=False),
            "semantic": AosSubsystemSection(available=False),
            "merge": AosSubsystemSection(available=False),
        }

    def collect_all(self):
        return self.sections


def test_doctor_report_only_suggests_commands(tmp_path) -> None:
    svc = AosService(str(tmp_path), collectors=FakeCollectors())
    result = svc.doctor(fix=False, confirm=False)
    assert not isinstance(result, Exception)
    assert result.fixed == []
    assert any(f.code == "blocked_tasks" for f in result.findings) or any(
        "blocked" in c for c in result.suggested_commands
    )
    assert any("worktree gc" in c or "lease" in c for c in result.suggested_commands)


def test_doctor_fix_without_confirm_errors(tmp_path) -> None:
    svc = AosService(str(tmp_path), collectors=FakeCollectors())
    result = svc.doctor(fix=True, confirm=False)
    assert isinstance(result, Exception)


def test_doctor_fix_with_confirm_calls_gc(tmp_path, monkeypatch) -> None:
    calls: list[str] = []

    def fake_fix(self) -> list[str]:
        calls.append("gc")
        return ["destroyed:wt-1"]

    svc = AosService(str(tmp_path), collectors=FakeCollectors(), fix_fn=fake_fix)
    result = svc.doctor(fix=True, confirm=True)
    assert not isinstance(result, Exception)
    assert calls == ["gc"]
    assert result.fixed
```

- [ ] **Step 2: Implement `doctor`**

Findings to emit when summary indicates:

- `leases_expired` / expired leases → `stale_lease` + suggest `metagit lease list` / note expire-on-list
- orphan/missing worktrees → suggest `metagit worktree gc`
- `blocked > 0` → `blocked_tasks`
- subsystem `available=False` for optional RFCs → `info` `subsystem_unavailable`
- merge pressure high (if summary has it) → warning
- `ready == 0` → info `empty_ready_set`

**Fix path (`fix=True`, `confirm=True`):**

1. Call `LeaseService.list()` (triggers `_expire_leases` side effect already in ACL).
2. Call `WorktreeService.gc()`.
3. Append human-readable strings to `fixed` (destroyed worktree ids / expired lease ids).

Never release claims, cancel merges, or mutate tasks.

- [ ] **Step 3: Tests pass**.

- [ ] **Step 4: Commit** `feat(aos): doctor report and gated ACL safe GC`

---

### Task 5: `next` (preview / commit / apply-hints)

**Files:**
- Create: `hints.py`
- Extend: `service.py`
- Test: `tests/core/aos/test_service_next.py`

- [ ] **Step 1: Write failing tests**

```python
#!/usr/bin/env python
"""AosService.next preview, commit, and apply-hints."""

from metagit.core.aos.service import AosService
from metagit.core.scheduler.models import ScheduleDecision


def test_next_preview_does_not_commit(tmp_path, monkeypatch) -> None:
    decisions = [
        ScheduleDecision(
            decision_id="d1",
            at="2026-07-09T00:00:00Z",
            graph_id="g1",
            node_id="n1",
            score=1.0,
            acl_commands=["metagit lease acquire --allocate"],
            compile_command="metagit context compile --project p --repo r --task-id n1",
        )
    ]

    class Sched:
        def preview_next(self, graph_id=None, *, limit=1):
            return decisions

        def next(self, graph_id=None, *, limit=1):
            raise AssertionError("next must not be called in preview")

    svc = AosService(str(tmp_path), scheduler=Sched())
    result = svc.next(commit=False, apply_hints=False)
    assert not isinstance(result, Exception)
    assert result.committed is False
    assert result.scheduler_available is True
    assert result.compile_command is not None
    assert result.hints_applied is False


def test_next_commit_delegates_to_scheduler_next(tmp_path) -> None:
    class Sched:
        def preview_next(self, graph_id=None, *, limit=1):
            raise AssertionError("preview must not be used when commit=True")

        def next(self, graph_id=None, *, limit=1):
            return [
                ScheduleDecision(
                    decision_id="d2",
                    at="2026-07-09T00:00:00Z",
                    graph_id="g1",
                    node_id="n1",
                    score=2.0,
                )
            ]

    svc = AosService(str(tmp_path), scheduler=Sched())
    result = svc.next(commit=True)
    assert not isinstance(result, Exception)
    assert result.committed is True
    assert result.decision is not None


def test_apply_hints_requires_agent_id(tmp_path) -> None:
    class Sched:
        def preview_next(self, graph_id=None, *, limit=1):
            return [
                ScheduleDecision(
                    decision_id="d1",
                    at="2026-07-09T00:00:00Z",
                    graph_id="g1",
                    node_id="n1",
                    score=1.0,
                    dispatch_hints={"project": "p", "repository": "p/r"},
                )
            ]

    svc = AosService(str(tmp_path), scheduler=Sched())
    result = svc.next(apply_hints=True, agent_id=None)
    assert isinstance(result, Exception)


def test_apply_hints_calls_binder(tmp_path) -> None:
    calls: list[str] = []

    class Sched:
        def preview_next(self, graph_id=None, *, limit=1):
            return [
                ScheduleDecision(
                    decision_id="d1",
                    at="2026-07-09T00:00:00Z",
                    graph_id="g1",
                    node_id="n1",
                    score=1.0,
                    dispatch_hints={"project": "p", "repository": "p/r", "title": "t"},
                    acl_commands=["x"],
                )
            ]

    def bind(**kwargs):
        calls.append(kwargs["agent_id"])
        return ["lease-1", "wt-1"]

    svc = AosService(str(tmp_path), scheduler=Sched(), apply_acl_fn=bind)
    result = svc.next(apply_hints=True, agent_id="agent-1")
    assert not isinstance(result, Exception)
    assert result.hints_applied is True
    assert calls == ["agent-1"]
```

- [ ] **Step 2: Implement `hints.py` + `next`**

`build_hints_from_decision(decision) -> (compile_command, acl_commands)` — prefer fields already on `ScheduleDecision`; if empty, rebuild like `SchedulerService._build_decision` / `TaskGraphService.bind_acl` command templates.

`apply_acl_binds(session_root, *, agent_id, project, repository, task_id, title, pattern="**/*")`:

1. `LeaseService.acquire(..., allocate_if_missing=True, task_id=task_id, agent_id=agent_id, repository=repository)`
2. `WorktreeService.create(...)` using the leased branch
3. `ClaimService.declare(..., pattern=pattern)`
4. Return ids / summary strings for `fixed`-style reporting on the next envelope (`reasons` or extend model with `applied: list[str]` if useful — prefer stuffing into `reasons` / keep `hints_applied` bool per design)

Do **not** shell out to CLI. Do **not** call context compile.

**Degrade:** if scheduler missing, use `TaskGraphService.ready()` first node and synthesize a minimal decision dict (`scheduler_available=False`). If no ready nodes, return empty envelope with reason `empty_ready_set`. If taskgraph missing, return `Exception`.

- [ ] **Step 3: Tests pass**.

- [ ] **Step 4: Commit** `feat(aos): next preview/commit and ACL apply-hints`

---

### Task 6: CLI (`aos` + `coord` alias)

**Files:**
- Create: `src/metagit/cli/commands/aos.py`
- Modify: `src/metagit/cli/main.py`
- Test: `tests/cli/commands/test_aos_cli.py`

- [ ] **Step 1: Write failing CLI tests** using CliRunner patterns from `tests/cli/commands/test_schedule_cli.py`:

  - `metagit aos status --json` returns subsystems
  - `metagit coord status --json` identical entrypoint (alias registered)
  - `metagit aos doctor --fix` without `--yes` exits non-zero
  - `metagit aos next --json` has `committed: false`

- [ ] **Step 2: Implement CLI**

```python
@click.group(name="aos")
@click.pass_context
def aos_group(ctx: click.Context) -> None:
    """Agent Operating System composition façade (RFC-0013)."""
    ...
```

Commands: `status`, `doctor` (`--fix`, `--yes`), `next` (`--commit`, `--apply-hints`, `--agent-id`, `--graph-id`), all with `--definition` + `--json` like schedule/ACL commands. Reuse `resolve_acl_roots` / `emit_json` / `raise_if_error` from `acl_common`.

In `main.py`:

```python
from metagit.cli.commands.aos import aos_group
cli.add_command(aos_group)
cli.add_command(aos_group, name="coord")
```

- [ ] **Step 3: Tests pass**.

- [ ] **Step 4: Commit** `feat(aos): CLI aos/coord status doctor next`

---

### Task 7: MCP tools + modality

**Files:**
- Modify: `tool_registry.py`, `runtime.py`, `scripts/modality-parity.yml`
- Test: `tests/core/mcp/test_aos_tools.py`

- [ ] **Step 1: Failing tests** — ACTIVE gate lists:

  - `metagit_aos_status`, `metagit_aos_doctor`, `metagit_aos_next`
  - `metagit_coord_status`, `metagit_coord_doctor`, `metagit_coord_next`

  Call `metagit_aos_status` and `metagit_coord_status` — both succeed with same shape.

  Doctor `fix=true` without `confirm=true` returns error payload.

- [ ] **Step 2: Register tools** — alias names dispatch to the same handler as primary (normalize name prefix).

Schemas:

- `metagit_aos_status`: `{}`
- `metagit_aos_doctor`: `{fix?: bool, confirm?: bool}`
- `metagit_aos_next`: `{commit?: bool, apply_hints?: bool, agent_id?: str, graph_id?: str, limit?: int}`

- [ ] **Step 3: Add modality `aos_status`** to `scripts/modality-parity.yml` mirroring `agent_scheduler` markers (CLI `aos.py`, MCP registry/runtime, `docs/reference/aos.md`, skills).

- [ ] **Step 4: Tests pass**.

- [ ] **Step 5: Commit** `feat(aos): MCP tools and aos_status modality parity`

---

### Task 8: Docs + skills

**Files:**
- Create: `docs/reference/aos.md`, `skills/metagit-aos/SKILL.md`
- Modify: `metagit-agent-coordination` skill (pointer), `docs/reference/agent-coordination.md`, `docs/agents.md`, `AGENTS.md`, `llms.txt`, `mkdocs.yml`, `CHANGELOG.md`
- Run: `task skills:sync` (or project equivalent) so `src/metagit/data/skills/` mirrors

- [ ] **Step 1: Write `docs/reference/aos.md`** with modality HTML comments:

```markdown
<!-- modality:aos_status -->

# Agent Operating System (RFC-0013)

Composition façade over ACL + task graph + optional 0009–0012.
...
```

Document CLI (`aos` / `coord`), MCP, doctor fix rules, next preview/commit/apply-hints, control loop.

- [ ] **Step 2: Write `skills/metagit-aos/SKILL.md`** — when to use `aos status|doctor|next`; loop: `aos next` → compile → ACL bind → work → complete → merge enqueue; never treat apply-hints as model launch.

- [ ] **Step 3: Add short pointer** under agent-coordination skill + reference doc linking to `aos.md`.

- [ ] **Step 4: Sync skills, update indexes/CHANGELOG**.

- [ ] **Step 5: Commit** `docs(aos): reference, skill, and registry links for RFC-0013`

---

### Task 9: Closeout

- [ ] **Step 1:** Update series index — RFC-0013 **Implemented**; Next MR note series complete (or follow-on beyond 0013).
- [ ] **Step 2:** Update `.mex/ROUTER.md` project state; add `.mex/patterns/aos-composition.md`.
- [ ] **Step 3:** `task qa:prepush` until green.
- [ ] **Step 4:** `task gitnexus:analyze`.
- [ ] **Step 5:** Commit closeout `docs: RFC-0013 AOS composition closeout`.

## Acceptance checklist

- [ ] `aos status --json` works with only 0007+0008 collectors available.
- [ ] Missing 0009–0012 → `available: false`, no crash.
- [ ] `coord` aliases identical to `aos`.
- [ ] Doctor without `--fix` never mutates; `--fix` without `--yes` errors; `--fix --yes` only lease expire-on-list + worktree gc.
- [ ] `next` preview does not append schedule decisions; `--commit` does.
- [ ] `--apply-hints` never launches models / never runs compile / only ACL APIs.
- [ ] Skill `metagit-aos` + coordination pointer + `docs/reference/aos.md` + modality `aos_status`.
- [ ] `task qa:prepush` green.

## Spec coverage (self-review)

| Spec requirement | Task |
|------------------|------|
| Thin `metagit.core.aos` | 1, 3–5 |
| `aos` + `coord` alias | 6, 7 |
| status / doctor / next | 3–5 |
| doctor `--fix --yes` safe GC | 4 |
| next preview / `--commit` / `--apply-hints` | 2, 5 |
| degrade without 0009–0012 | 3, 5 |
| skill + pointer | 8 |
| modality `aos_status` | 7–8 |
| no new persistence / engines | global constraints |
| series closeout | 9 |

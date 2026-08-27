# RFC-0021: Multi-Agent Scenario Test Harness — Design

**Status:** Proposed  
**Date:** 2026-08-27  
**Series:** [Agent Reliability series index](2026-08-27-agent-reliability-series-index.md)  
**Depends on:** RFC-0007 (ACL), RFC-0008 (task graph), RFC-0012 (scheduler), RFC-0013 (AOS), RFC-0015 (DocumentStore / `InMemoryDocumentStore`); optionally RFC-0017 (harness runs), RFC-0019 (crash recovery / `aos recover`)  
**Plan:** (pending)  
**Audience:** Contributors hardening multi-agent coordination paths in metagit-cli

## Summary

Introduce a **`tests/scenarios/` harness** that exercises real coordination engines (ACL, task graph, scheduler, AOS, optional plane DocumentStore) against **ephemeral temp workspaces** with **deterministic multi-agent concurrency**. The harness simulates 2+ agents using threads (and optionally subprocesses for crash isolation) without launching external model runtimes.

Five core scenarios ship in CI: **lease contention**, **claim overlap**, **concurrent `aos next`**, **crash recovery**, and **remote-state CAS conflicts**. Each scenario asserts stable outcomes, emits structured diagnostics on failure, and reuses patterns already proven in unit tests (`tmp_path` workspaces, injectable clocks, stub schedulers, `CliRunner` JSON paths).

## Goals

1. Provide a **shared scenario bootstrap** (manifest + git repos + ready task nodes) so multi-agent tests do not duplicate `_init_repo` / `.metagit.yml` boilerplate.
2. Run **≥5 deterministic scenarios** in CI that cover the failure modes called out in the reliability series.
3. Support **optional `InMemoryDocumentStore`** (RFC-0015) for CAS conflict scenarios without cloud deps.
4. Produce **actionable failure output**: agent timeline, persisted artifacts snapshot, and suggested `aos doctor` commands.
5. Align with existing pytest conventions (shebang, `tmp_path`, `Exception` union returns, `--json` CLI smoke).
6. Document how to add scenarios and how nightly vs PR CI tiers are selected.

## Non-Goals

- A new agent runtime, model launcher, or fleet orchestrator.
- Replacing existing unit tests under `tests/core/` and `tests/cli/` — scenarios complement, not supersede, them.
- End-to-end MCP stdio multi-process fleets (defer until a scenario proves CLI/service layer insufficient).
- Cloud DocumentStore backends in default CI (DynamoDB/Mongo optional follow-up markers).
- Performance/load testing at org scale (that belongs in RFC-0025 indexing benchmarks).
- Implementing RFC-0019 `aos recover` inside this RFC — scenarios **assert doctor findings** now and **wire recover** when 0019 lands.

## Decisions (locked)

| # | Decision |
|---|----------|
| D1 | Scenarios live under **`tests/scenarios/`** with a small **`tests/scenarios/harness/`** library (not `src/` — test-only). |
| D2 | Default concurrency model is **`threading`** against shared in-process services; subprocess agents are opt-in per scenario for crash isolation. |
| D3 | Determinism uses **injectable clocks** (`now_fn` / `clock_fn`, already on `LeaseService`) and **thread `Barrier`** start gates — never `sleep()` for correctness. |
| D4 | Workspaces are **`tmp_path`-scoped** per test; no reuse across tests. |
| D5 | **`InMemoryDocumentStore`** is the default plane backend for CAS scenarios; local JSON and HTTP stub (`tests/core/state/conftest.py`) are secondary variants behind markers. |
| D6 | Scenarios invoke **real services** (`BranchService`, `LeaseService`, `TaskGraphService`, `SchedulerService`, `AosService`) — not reimplemented logic. CLI coverage uses `CliRunner` where the scenario validates the operator path. |
| D7 | **PR CI** runs the five core scenarios (target ≤ 60s total); **`@pytest.mark.nightly`** covers subprocess crash + HTTP stub variants. |
| D8 | **`METAGIT_AGENT_MODE`** is set explicitly in agent-thread scenarios that require JSON-only CLI behavior; global conftest continues clearing it by default. |
| D9 | Failure diagnostics are **structured dicts** (JSON-serializable) attached via pytest `record_property` or caplog — not ad-hoc print. |

## Architecture

```text
tests/scenarios/
├── README.md                 # how to run, add scenarios, read failures
├── conftest.py               # markers, session fixtures, diagnostic hooks
├── harness/
│   ├── __init__.py
│   ├── workspace.py          # ScenarioWorkspace bootstrap
│   ├── agents.py             # SimulatedAgent + AgentPool
│   ├── clock.py              # ControllableClock (wraps LeaseService hooks)
│   ├── diagnostics.py        # snapshot + timeline on assertion failure
│   └── plane.py              # memory | local | http-stub DocumentStore factory
├── test_lease_contention.py
├── test_claim_overlap.py
├── test_concurrent_aos_next.py
├── test_crash_recovery.py
└── test_cas_conflict.py
```

```text
┌─────────────────────────────────────────────────────────────┐
│ pytest test (tmp_path)                                       │
│   ScenarioWorkspace.bootstrap()                              │
│     ├─ .metagit.yml (demo project, service-a repo)           │
│     ├─ git init + README (GitPython, same as unit tests)     │
│     ├─ task graph: 2+ ready nodes                            │
│     └─ optional StateConfig → InMemoryDocumentStore          │
└───────────────────────────┬─────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
   SimulatedAgent A   SimulatedAgent B   (optional) crash stub
         │                  │                  │
         └──────────┬───────┴──────────────────┘
                    ▼
         Real coordination services (0007–0013)
                    ▼
         harness.diagnostics.assert_scenario(...)
```

### Relationship to existing tests

| Existing pattern | Location | Reuse in scenarios |
|------------------|----------|-------------------|
| Temp workspace + git repo | `tests/core/coordination/test_coordination_services.py` (`workspace` fixture, `_init_repo`) | `ScenarioWorkspace` extracts this |
| Injectable time / lease expiry | `test_lease_auto_expires` | `ControllableClock` shared fixture |
| Scheduler commit vs preview | `tests/core/scheduler/test_preview_next.py`, `test_service.py` | concurrent `aos next` baseline |
| AOS preview/commit delegation | `tests/core/aos/test_service_next.py` | thread-safe `AosService.next(commit=True)` |
| ACL bind hints | `tests/core/taskgraph/test_bind_acl.py` | seed nodes with `bind_acl` |
| CLI JSON smoke | `tests/cli/commands/test_acl_cli.py` | optional CLI variant scenarios |
| HTTP CAS stub | `tests/core/state/conftest.py` (`remote_stub_server`) | CAS conflict HTTP marker |
| In-memory plane | `tests/core/state/test_memory_store.py` | default CAS backend |

## Harness interfaces (test-only)

### `ScenarioWorkspace`

Bootstrap API (proposed):

```python
class ScenarioWorkspace:
  root: Path
  manifest_path: Path

  @classmethod
  def bootstrap(
    cls,
    tmp_path: Path,
    *,
    repos: list[str] | None = None,
    ready_nodes: int = 2,
    state_backend: Literal["local", "memory", "http-stub"] = "local",
  ) -> ScenarioWorkspace: ...

  def branch_service(self) -> BranchService: ...
  def lease_service(self, *, clock: ControllableClock | None = None) -> LeaseService: ...
  def task_graph(self) -> TaskGraphService: ...
  def scheduler(self) -> SchedulerService: ...
  def aos(self) -> AosService: ...
  def document_store(self) -> DocumentStore | None: ...
  def snapshot(self) -> dict[str, Any]: ...  # leases, claims, decisions, tasks
```

Manifest content mirrors unit-test fixtures: one project `demo`, repo `demo/service-a`, default worktrees path, minimal valid `.metagit.yml`.

### `SimulatedAgent`

Minimal agent loop — no model calls:

```python
class SimulatedAgent:
  agent_id: str

  def allocate_and_lease(self, ws: ScenarioWorkspace, *, task_id: str) -> LeaseResult | Exception: ...
  def declare_claim(self, ws: ScenarioWorkspace, *, patterns: list[str]) -> ...: ...
  def aos_next(self, ws: ScenarioWorkspace, *, commit: bool = True) -> AosNextResult | Exception: ...
  def complete_task(self, ws: ScenarioWorkspace, *, node_id: str) -> ...: ...
```

`AgentPool.run_barrier(actions: list[Callable[[SimulatedAgent], T]])` starts N threads at a `Barrier`, collects results in deterministic `agent_id` order.

### `diagnostics`

On failure, emit:

- `timeline[]`: `{at, agent_id, action, outcome, error?}`
- `workspace_snapshot`: output of `ScenarioWorkspace.snapshot()`
- `suggested_commands[]`: strings suitable for `aos doctor` / manual inspection
- `artifact_paths`: key files under `.metagit/` (leases, schedule decisions, task nodes)

## Scenario catalog

### S1 — Lease contention (`test_lease_contention.py`)

**Story:** Agents A and B race for the same branch; B fails while A holds the lease; after controlled expiry B succeeds.

| Step | Agent A | Agent B |
|------|---------|---------|
| 1 | `branch.allocate` + `lease.acquire` (ttl=60s) | — |
| 2 | — | `lease.acquire` same branch → **error** |
| 3 | clock +120s | — |
| 4 | — | `lease.acquire` → **success** |

**Asserts:** Second acquire returns `Exception`; expired lease status; event feed contains ACL events; exactly one active lease between steps 1–3.

**Conventions mirrored:** `test_lease_blocks_second_agent`, `test_lease_auto_expires`.

---

### S2 — Claim overlap (`test_claim_overlap.py`)

**Story:** A declares `backend/auth/*`; B attempts overlapping declare and check.

| Step | Agent A | Agent B |
|------|---------|---------|
| 1 | `claim.declare(patterns=["backend/auth/*"])` | — |
| 2 | — | `claim.check(patterns=["backend/auth/token.py"])` → conflicts |
| 3 | — | `claim.declare(..., allow_conflicts=False)` → **blocked** |

**Asserts:** `check.conflicts[0].owner == agent-a`; declare with `allow_conflicts=False` returns conflict result; non-overlapping patterns from C succeed.

**Conventions mirrored:** `test_claim_overlap_detection`.

---

### S3 — Concurrent `aos next` (`test_concurrent_aos_next.py`)

**Story:** Two agents call `AosService.next(commit=True)` against a scheduler with two ready nodes; each receives a distinct node; no duplicate `node_id` in persisted decisions.

| Step | Agents A + B (barrier) |
|------|------------------------|
| 1 | Seed graph with nodes `n1`, `n2` (ready, distinct repos or priorities) |
| 2 | Parallel `aos.next(commit=True, agent_id=…)` |
| 3 | Verify `ScheduleStore.list_decisions()` has 2 rows, unique `node_id` |

**Asserts:** Both calls succeed; decision set is `{n1, n2}` (order-independent); preview path (`commit=False`) leaves decisions empty (regression guard from `test_preview_next_does_not_append_decisions`).

**Edge case subtest:** Single ready node → exactly one agent gets a decision; the other gets empty/skipped per scheduler policy (document expected behavior in assertion message).

---

### S4 — Crash recovery (`test_crash_recovery.py`)

**Story:** Agent A acquires lease and creates worktree; process exits without release; doctor reports findings; safe GC path clears stale resources.

| Step | Agent A |
|------|---------|
| 1 | full ACL bind: allocate → lease → worktree |
| 2 | simulate crash (drop references; optionally subprocess kill) |
| 3 | `aos.doctor()` → findings include expired/orphan lease/worktree |
| 4 | `aos.doctor(fix=True, confirm=True)` **or** future `aos recover` → GC |

**Asserts:** Doctor lists actionable commands before fix; after fix, lease not active and worktree destroyed; task node remains addressable (not silently deleted).

**Dependency note:** Until RFC-0019 ships, scenario validates **doctor report + existing `--fix` GC** only; recover subtest is `@pytest.mark.skip` with linked issue.

**Conventions mirrored:** `test_worktree_create_requires_lease_and_isolates`, `test_service_doctor.py`.

---

### S5 — Remote-state CAS conflict (`test_cas_conflict.py`)

**Story:** Two agents read the same coordination document, both write with stale token; one loses CAS; retry with fresh token succeeds.

| Step | Agent A | Agent B |
|------|---------|---------|
| 1 | `store.get(ref)` → token T0 | `store.get(ref)` → token T0 |
| 2 | `put(..., expected=T0)` → OK | — |
| 3 | — | `put(..., expected=T0)` → **`StateConflictError`** |
| 4 | — | re-get → `put(..., expected=T1)` → OK |

**Backends:**

| Marker | Backend |
|--------|---------|
| (default) | `InMemoryDocumentStore` |
| `@pytest.mark.scenario_http` | `remote_stub_server` + `HttpDocumentStore` |
| `@pytest.mark.nightly` | both backends |

**Asserts:** Exactly one winner on stale CAS; final document matches last successful writer; no torn envelope (objectives/handoffs shape preserved).

**Conventions mirrored:** `tests/core/state/test_http_document_store.py`, `test_memory_store.py`.

---

### Optional S6 — Concurrent harness next (RFC-0017 follow-on)

When RFC-0017 lands, add `test_concurrent_harness_next.py`: two agents cannot receive the same leased task node. Mark **`@pytest.mark.requires_harness`** until envelope persistence exists. Not counted toward the initial five.

## Persistence & backends

| Layer | Default in scenarios | Notes |
|-------|---------------------|-------|
| ACL / task / schedule | Local JSON under `tmp_path/.metagit/` | Same layout as production |
| Git repos | Real git via GitPython | Required for branch/worktree scenarios |
| Plane / coord docs | `InMemoryDocumentStore` for S5 | Shared store injected into workspace config |
| HTTP remote | Stub server fixture | Optional marker; reuses state conftest handler |

Environment variables scenarios may set per-test via `monkeypatch`:

- `METAGIT_STATE_BACKEND=memory` (when wired through `StateConfig`)
- `METAGIT_AGENT_MODE=true` for CLI JSON scenarios

## CI integration

| Tier | Command | Scope |
|------|---------|-------|
| PR / prepush | extend integration pass | `pytest tests/scenarios -m "not nightly" -v` |
| Nightly workflow | new job or schedule | `pytest tests/scenarios -m nightly -v` |
| Local dev | documented in README | `uv run pytest tests/scenarios -v` |

**Prepush gate change (plan phase):** add `tests/scenarios` to the integration pytest invocation in `scripts/prepush-gate.py` when any file under `tests/scenarios/` or touched coordination modules changes.

**Markers (register in `tests/scenarios/conftest.py`):**

```python
pytest.mark.nightly
pytest.mark.scenario_http
pytest.mark.requires_harness  # RFC-0017
pytest.mark.subprocess_isolation
```

**Timeout budget:** each scenario ≤ 10s on CI runners; barrier threads join with explicit timeout and diagnostic dump on hang.

## Acceptance

- [ ] `tests/scenarios/` exists with harness module and README.
- [ ] **Five scenarios** (S1–S5) pass deterministically on Linux/macOS CI (10 consecutive runs without flake).
- [ ] Failure output includes timeline + workspace snapshot + suggested doctor commands.
- [ ] PR CI runs non-nightly scenarios; nightly job covers HTTP CAS + subprocess crash variant.
- [ ] No new runtime dependencies (stdlib threading + existing test extras only).
- [ ] Agent reliability series index and `.mex/ROUTER.md` updated when implemented.
- [ ] Implementation plan written under `docs/superpowers/plans/2026-08-27-rfc-0021-multi-agent-scenarios.md`.

## Dependencies

| Depends on | Provides to |
|------------|-------------|
| RFC-0007–0013 shipped engines | RFC-0019 crash-recovery scenarios (doctor/recover assertions) |
| RFC-0015 `InMemoryDocumentStore` | S5 without cloud |
| RFC-0017 harness (optional) | S6 concurrent envelope |
| RFC-0019 recover (optional) | S4 full recover path |

**Parallel work:** RFC-0021 can start before RFC-0019; S4 uses doctor/`--fix` first.

## Documentation (implementation phase)

- `tests/scenarios/README.md` — run commands, marker matrix, how to add S7+.
- Link from `docs/reference/agent-coordination.md` § Testing multi-agent safety.
- Link from `docs/agents-quickstart.md` troubleshooting (“flaky lease?” → scenarios).
- No public `docs/reference/rfc-0021*` stub until shipped.

## Open questions

1. **Subprocess vs in-process for S4 crash?**  
   **Recommendation:** in-process for PR CI; subprocess kill behind `@pytest.mark.nightly` to validate no stale file handles.

2. **Include CLI-level concurrent scenarios (two `CliRunner`s in threads)?**  
   **Recommendation:** one CLI smoke scenario (`test_acl_cli`-style) in nightly only; service-layer scenarios are primary for determinism.

3. **Should scenarios seed via `metagit task create/expand` CLI or `TaskGraphService` directly?**  
   **Recommendation:** service directly for speed; one CLI e2e scenario ensures flag parity.

4. **Wire scenarios into modality parity?**  
   **Recommendation:** no — test harness only; no new agent-facing surface.

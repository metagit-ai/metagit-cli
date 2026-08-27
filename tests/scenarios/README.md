# Multi-agent scenario harness (RFC-0021)

Deterministic multi-agent coordination tests against ephemeral `tmp_path` workspaces.
Scenarios call real ACL / task-graph / scheduler / AOS services (and optional
`InMemoryDocumentStore`) without launching model runtimes.

## Run

```bash
# All non-nightly scenarios (PR / local default)
uv run pytest tests/scenarios -m "not nightly" -v

# Everything under tests/scenarios
uv run pytest tests/scenarios -v

# Nightly-only markers (HTTP stub / subprocess variants when present)
uv run pytest tests/scenarios -m nightly -v
```

## Catalog

| ID | File | Story |
|----|------|--------|
| S1 | `test_lease_contention.py` | Two agents race one branch; second fails, then succeeds after controlled expiry |
| S2 | `test_claim_overlap.py` | Overlapping claim check/declare blocked; non-overlap succeeds |
| S3 | `test_concurrent_aos_next.py` | Concurrent `aos next` preview does not crash; commit appends without crash |
| S4 | `test_crash_recovery.py` | Crash mid-lease → `aos doctor` findings → `--fix` GC; task node retained |
| S5 | `test_cas_conflict.py` | Two writers, stale CAS token loses; retry with fresh token wins |
| opt | `test_run_ledger_concurrent.py` | Concurrent run-ledger `open_run` writers (RFC-0017 pattern) |

## Harness layout

```text
tests/scenarios/
├── README.md
├── conftest.py          # markers + scenario_workspace fixture
├── harness/
│   ├── workspace.py     # ScenarioWorkspace.bootstrap(...)
│   ├── agents.py        # SimulatedAgent + AgentPool.run_barrier
│   ├── clock.py         # ControllableClock
│   ├── diagnostics.py   # timeline + snapshot on failure
│   └── plane.py         # memory | local | http-stub store factory
└── test_*.py
```

## Adding a scenario

1. Bootstrap with `ScenarioWorkspace.bootstrap(tmp_path, ready_nodes=…)`.
2. Drive agents via `SimulatedAgent` / `AgentPool.run_barrier` (use `Barrier`, not `sleep`).
3. Prefer injectable `ControllableClock` for lease expiry.
4. On hard asserts, use `assert_scenario(..., diagnostics=…)` so failures include timeline + snapshot + suggested `aos doctor` commands.
5. Mark heavy variants `@pytest.mark.nightly` (and `@pytest.mark.scenario_http` for HTTP stub).

## Markers

| Marker | Meaning |
|--------|---------|
| `nightly` | Optional CI job; skipped from default `-m "not nightly"` |
| `scenario_http` | Needs HTTP DocumentStore stub |
| `requires_harness` | Needs RFC-0017 harness envelope |
| `subprocess_isolation` | Crash via subprocess kill |
| `slow` | May exceed typical unit-test budgets |

## Design

See [RFC-0021 design](../../docs/superpowers/specs/2026-08-27-rfc-0021-multi-agent-scenarios-design.md).

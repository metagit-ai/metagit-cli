#!/usr/bin/env python
"""S3 — concurrent aos next preview / commit without crash."""

from __future__ import annotations

from pathlib import Path

from metagit.core.aos.models import AosNextResult
from metagit.core.scheduler.store import ScheduleStore

from tests.scenarios.harness.agents import AgentPool
from tests.scenarios.harness.diagnostics import ScenarioDiagnostics, assert_scenario
from tests.scenarios.harness.workspace import ScenarioWorkspace


def test_concurrent_aos_next_preview_no_crash(tmp_path: Path, record_property) -> None:
    ws = ScenarioWorkspace.bootstrap(tmp_path, ready_nodes=2)
    diag = ScenarioDiagnostics(ws)
    pool = AgentPool(["agent-a", "agent-b"])

    results = pool.run_barrier(
        [
            lambda agent: agent.aos_next(ws, commit=False),
            lambda agent: agent.aos_next(ws, commit=False),
        ]
    )
    for agent_id, result in zip(["agent-a", "agent-b"], results, strict=True):
        assert_scenario(
            isinstance(result, AosNextResult),
            diag,
            message=f"{agent_id} preview must succeed without crash",
            record_property=record_property,
        )
        assert isinstance(result, AosNextResult)
        diag.record(agent_id=agent_id, action="aos.next(preview)", outcome="ok")
        assert result.committed is False

    decisions = ScheduleStore(str(ws.root)).list_decisions()
    assert not isinstance(decisions, Exception)
    assert_scenario(
        decisions == [],
        diag,
        message="preview must leave schedule decisions empty",
        record_property=record_property,
    )


def test_concurrent_aos_next_commit_no_crash(tmp_path: Path, record_property) -> None:
    ws = ScenarioWorkspace.bootstrap(tmp_path, ready_nodes=2)
    diag = ScenarioDiagnostics(ws)
    pool = AgentPool(["agent-a", "agent-b"])

    results = pool.run_barrier(
        [
            lambda agent: agent.aos_next(ws, commit=True),
            lambda agent: agent.aos_next(ws, commit=True),
        ]
    )
    for agent_id, result in zip(["agent-a", "agent-b"], results, strict=True):
        assert_scenario(
            isinstance(result, AosNextResult),
            diag,
            message=f"{agent_id} commit must succeed without crash",
            record_property=record_property,
        )
        assert isinstance(result, AosNextResult)
        diag.record(agent_id=agent_id, action="aos.next(commit)", outcome="ok")

    decisions = ScheduleStore(str(ws.root)).list_decisions()
    assert not isinstance(decisions, Exception)
    assert_scenario(
        len(decisions) >= 1,
        diag,
        message="at least one committed decision should be persisted",
        record_property=record_property,
    )


def test_sequential_aos_next_commit_unique_nodes(tmp_path: Path, record_property) -> None:
    """With two ready nodes, two sequential commits can cover both when callers filter."""
    ws = ScenarioWorkspace.bootstrap(tmp_path, ready_nodes=2)
    diag = ScenarioDiagnostics(ws)
    decided: set[str] = set()

    def ready_excluding(_graph_id):
        ready = ws.task_graph().ready(ws.graph_id)
        if isinstance(ready, Exception):
            return ready
        return [node for node in ready if node.node_id not in decided]

    ws._scheduler = None  # noqa: SLF001 — rebuild with filtered ready_fn
    from metagit.core.scheduler.service import SchedulerService

    ws._scheduler = SchedulerService(  # noqa: SLF001
        str(ws.root),
        ready_fn=ready_excluding,
        worktrees_fn=lambda: [],
        merge_status_fn=lambda: [],
        now_fn=ws.clock.now_iso,
    )
    ws._aos = None  # noqa: SLF001

    first = ws.aos().next(commit=True)
    assert not isinstance(first, Exception)
    assert first.decision is not None
    decided.add(str(first.decision["node_id"]))
    second = ws.aos().next(commit=True)
    assert not isinstance(second, Exception)
    assert second.decision is not None
    decided.add(str(second.decision["node_id"]))

    assert_scenario(
        decided == {"n1", "n2"},
        diag,
        message="sequential commits with exclusion should cover both ready nodes",
        record_property=record_property,
    )

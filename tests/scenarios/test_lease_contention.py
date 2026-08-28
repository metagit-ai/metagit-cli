#!/usr/bin/env python
"""S1 — lease contention between two agents."""

from __future__ import annotations

from pathlib import Path

from tests.scenarios.harness.agents import SimulatedAgent
from tests.scenarios.harness.diagnostics import ScenarioDiagnostics, assert_scenario
from tests.scenarios.harness.workspace import ScenarioWorkspace


def test_lease_contention_second_agent_fails_then_succeeds_after_expiry(
    tmp_path: Path,
    record_property,
) -> None:
    ws = ScenarioWorkspace.bootstrap(tmp_path, ready_nodes=0)
    diag = ScenarioDiagnostics(ws)
    agent_a = SimulatedAgent("agent-a")
    agent_b = SimulatedAgent("agent-b")

    lease_a = agent_a.allocate_and_lease(ws, task_id="t-a", ttl="60")
    assert_scenario(
        not isinstance(lease_a, Exception),
        diag,
        message="agent-a should acquire lease",
        record_property=record_property,
    )
    diag.record(agent_id="agent-a", action="lease.acquire", outcome="ok")

    blocked = agent_b.allocate_and_lease(
        ws,
        task_id="t-b",
        ttl="60",
        branch=lease_a.branch,
    )
    assert_scenario(
        isinstance(blocked, Exception),
        diag,
        message="agent-b must fail while agent-a holds the lease",
        record_property=record_property,
    )
    diag.record(
        agent_id="agent-b",
        action="lease.acquire",
        outcome="blocked",
        error=str(blocked),
    )

    active = ws.lease_service().list(status="active")
    assert not isinstance(active, Exception)
    assert_scenario(
        len(active.leases) == 1 and active.leases[0].agent_id == "agent-a",
        diag,
        message="exactly one active lease while agent-a holds it",
        record_property=record_property,
    )

    ws.clock.advance(seconds=120)
    listed = ws.lease_service().list()
    assert not isinstance(listed, Exception)
    assert_scenario(
        listed.leases[0].status == "expired",
        diag,
        message="lease should expire after controlled clock advance",
        record_property=record_property,
    )

    lease_b = agent_b.allocate_and_lease(
        ws,
        task_id="t-b",
        ttl="60",
        branch=lease_a.branch,
    )
    assert_scenario(
        not isinstance(lease_b, Exception),
        diag,
        message="agent-b should acquire after expiry",
        record_property=record_property,
    )
    diag.record(agent_id="agent-b", action="lease.acquire", outcome="ok")

#!/usr/bin/env python
"""S4 — crash mid-lease recovery via aos doctor report / GC."""

from __future__ import annotations

from pathlib import Path

import pytest

from metagit.core.aos.service import AosService
from metagit.core.coordination.worktree_service import WorktreeService

from tests.scenarios.harness.agents import SimulatedAgent
from tests.scenarios.harness.diagnostics import ScenarioDiagnostics, assert_scenario
from tests.scenarios.harness.workspace import ScenarioWorkspace


def test_crash_mid_lease_doctor_reports_and_gc(tmp_path: Path, record_property) -> None:
    ws = ScenarioWorkspace.bootstrap(tmp_path, ready_nodes=1)
    diag = ScenarioDiagnostics(ws)
    agent = SimulatedAgent("agent-a")

    lease = agent.allocate_and_lease(ws, task_id="crash-1", ttl="60")
    assert_scenario(
        not isinstance(lease, Exception),
        diag,
        message="lease acquire before crash",
        record_property=record_property,
    )
    worktrees = WorktreeService(
        str(ws.root),
        sync_root=str(ws.root),
        definition_path=str(ws.manifest_path),
        lease_service=ws.lease_service(),
        now_fn=ws.clock.now_iso,
    )
    wt = worktrees.create(
        repository=ws.default_repository,
        agent_id="agent-a",
        task_id="crash-1",
        branch=lease.branch,
    )
    assert_scenario(
        not isinstance(wt, Exception),
        diag,
        message="worktree create before crash",
        record_property=record_property,
    )
    diag.record(agent_id="agent-a", action="acl.bind", outcome="ok")

    # Simulate crash: drop live service handles; persisted ACL state remains.
    del agent
    del worktrees
    ws._leases = None  # noqa: SLF001
    ws._worktrees = None  # noqa: SLF001
    ws._aos = None  # noqa: SLF001

    ws.clock.advance(seconds=120)
    expired = ws.lease_service().list()
    assert not isinstance(expired, Exception)
    assert_scenario(
        any(row.status == "expired" for row in expired.leases),
        diag,
        message="lease must expire after crash + clock advance",
        record_property=record_property,
    )

    # Doctor uses wall-clock collectors; expired status is already persisted on disk.
    doctor = AosService(str(ws.root)).doctor(fix=False, confirm=False)
    assert not isinstance(doctor, Exception)
    codes = {finding.code for finding in doctor.findings}
    assert_scenario(
        "stale_lease" in codes,
        diag,
        message="doctor should report stale_lease after crash",
        record_property=record_property,
    )
    assert_scenario(
        any("worktree gc" in cmd or "lease" in cmd for cmd in doctor.suggested_commands),
        diag,
        message="doctor should suggest actionable lease/worktree commands",
        record_property=record_property,
    )
    diag.record(agent_id="system", action="aos.doctor", outcome="findings")

    fixed = AosService(str(ws.root)).doctor(fix=True, confirm=True)
    assert not isinstance(fixed, Exception)
    assert_scenario(
        any(item.startswith("worktree_destroyed:") for item in fixed.fixed),
        diag,
        message="doctor --fix should GC orphan worktree",
        record_property=record_property,
    )

    after = WorktreeService(str(ws.root)).list(status="active")
    assert not isinstance(after, Exception)
    assert_scenario(
        after.worktrees == [],
        diag,
        message="no active worktrees after GC",
        record_property=record_property,
    )

    nodes = ws.task_graph().list_nodes()
    assert not isinstance(nodes, Exception)
    assert_scenario(
        any(node.node_id == "n1" for node in nodes),
        diag,
        message="task node must remain addressable after recovery GC",
        record_property=record_property,
    )


@pytest.mark.skip(reason="RFC-0019 aos recover not shipped yet")
def test_aos_recover_path_deferred(tmp_path: Path) -> None:
    _ = tmp_path
    raise AssertionError("unreachable until RFC-0019")

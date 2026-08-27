#!/usr/bin/env python
"""S2 — advisory claim overlap detection."""

from __future__ import annotations

from pathlib import Path

from metagit.core.coordination.models import ClaimCheckResult

from tests.scenarios.harness.agents import SimulatedAgent
from tests.scenarios.harness.diagnostics import ScenarioDiagnostics, assert_scenario
from tests.scenarios.harness.workspace import ScenarioWorkspace


def test_claim_overlap_detection(tmp_path: Path, record_property) -> None:
    ws = ScenarioWorkspace.bootstrap(tmp_path, ready_nodes=0)
    diag = ScenarioDiagnostics(ws)
    agent_a = SimulatedAgent("agent-a")
    agent_b = SimulatedAgent("agent-b")
    agent_c = SimulatedAgent("agent-c")

    declared = agent_a.declare_claim(ws, patterns=["backend/auth/*"])
    assert_scenario(
        not isinstance(declared, Exception),
        diag,
        message="agent-a claim declare should succeed",
        record_property=record_property,
    )
    diag.record(agent_id="agent-a", action="claim.declare", outcome="ok")

    check = agent_b.check_claim(ws, patterns=["backend/auth/token.py"])
    assert_scenario(
        not isinstance(check, Exception) and bool(check.conflicts),
        diag,
        message="agent-b check should report conflicts",
        record_property=record_property,
    )
    assert check.conflicts[0].owner == "agent-a"
    diag.record(agent_id="agent-b", action="claim.check", outcome="conflict")

    blocked = agent_b.declare_claim(
        ws,
        patterns=["backend/auth/*"],
        allow_conflicts=False,
    )
    assert_scenario(
        isinstance(blocked, ClaimCheckResult) and bool(blocked.conflicts),
        diag,
        message="overlapping declare with allow_conflicts=False must be blocked",
        record_property=record_property,
    )
    diag.record(agent_id="agent-b", action="claim.declare", outcome="blocked")

    ok = agent_c.declare_claim(ws, patterns=["frontend/*"], allow_conflicts=False)
    assert_scenario(
        not isinstance(ok, Exception) and not isinstance(ok, ClaimCheckResult),
        diag,
        message="non-overlapping claim from agent-c should succeed",
        record_property=record_property,
    )
    diag.record(agent_id="agent-c", action="claim.declare", outcome="ok")

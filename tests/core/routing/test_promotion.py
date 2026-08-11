#!/usr/bin/env python
"""Unit tests for routing promotion policy and run lifecycle invariants."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from metagit.core.config.models import MetagitConfig, RoutingConfig, RoutingPolicy
from metagit.core.routing.models import RequestClass, Run
from metagit.core.routing.promotion import evaluate
from metagit.core.routing.routing_service import RoutingService


def default_policy() -> RoutingPolicy:
    return RoutingPolicy()


def _run(idx: int, outcome: str | None) -> Run:
    closed = f"2026-08-10T12:{idx:02d}:00Z" if outcome is not None else None
    return Run(
        id=f"RUN-20260810-12{idx:02d}00-REQ-X",
        **{"class": "REQ-X"},
        tier="skilled",
        actor="tester",
        opened=f"2026-08-10T12:{idx:02d}:00Z",
        outcome=outcome,
        closed=closed,
    )


def landed_run(idx: int) -> Run:
    return _run(idx, "landed")


def bounced_run(idx: int) -> Run:
    return _run(idx, "bounced")


def noop_run(idx: int) -> Run:
    return _run(idx, "noop")


def abandoned_run(idx: int) -> Run:
    return _run(idx, "abandoned")


def test_mutating_class_never_reaches_deterministic() -> None:
    cls = RequestClass(id="REQ-X", title="t", mutates=True, tier="skilled")
    runs = [landed_run(i) for i in range(20)]
    tier, _, _ = evaluate(cls, runs, default_policy())
    assert tier == "skilled"


def test_deterministic_requires_an_executor() -> None:
    cls = RequestClass(id="REQ-X", title="t", mutates=False, tier="skilled", executor=None)
    tier, state, _ = evaluate(cls, [landed_run(i) for i in range(5)], default_policy())
    assert tier == "skilled"
    assert state == "ready-needs-executor"


def test_nonmutating_with_executor_promotes() -> None:
    cls = RequestClass(id="REQ-X", title="t", mutates=False, tier="skilled", executor="run-report")
    tier, _, _ = evaluate(cls, [landed_run(i) for i in range(5)], default_policy())
    assert tier == "deterministic"


def test_single_bounce_demotes_immediately() -> None:
    cls = RequestClass(id="REQ-X", title="t", mutates=False, tier="deterministic", executor="x")
    tier, state, _ = evaluate(cls, [landed_run(0), bounced_run(1)], default_policy())
    assert tier == "skilled"
    assert state.startswith("demoted:")


def test_noop_never_counts_as_clean() -> None:
    cls = RequestClass(id="REQ-X", title="t", mutates=False, tier="skilled", executor="x")
    runs = [landed_run(i) for i in range(4)] + [noop_run(4)]
    tier, _, _ = evaluate(cls, runs, default_policy())
    assert tier == "novel"


def test_abandoned_is_neutral() -> None:
    cls = RequestClass(id="REQ-X", title="t", mutates=True, tier="novel")
    runs = [landed_run(i) for i in range(5)] + [abandoned_run(5)]
    tier, _, _ = evaluate(cls, runs, default_policy())
    assert tier == "skilled"


def test_open_run_has_no_outcome_and_that_is_legal() -> None:
    run = Run(
        id="RUN-20260810-120000-REQ-X",
        **{"class": "REQ-X"},
        tier="skilled",
        actor="tester",
        opened="2026-08-10T12:00:00Z",
    )
    assert run.outcome is None


def test_close_refuses_to_rewrite_a_closed_run(tmp_path: Path) -> None:
    now = datetime(2026, 8, 10, 12, 0, 0, tzinfo=timezone.utc)
    config = MetagitConfig(
        name="demo",
        routing=RoutingConfig(
            catalog="knowledge/requests/entries",
            runs="knowledge/requests/runs",
        ),
    )
    service = RoutingService(config, workspace_root=str(tmp_path), now_fn=lambda: now)

    req = RequestClass(id="REQ-X", title="Rotate cert", tier="skilled", mutates=True)
    service.class_store.save(req, expected=None)

    opened = service.open_run(class_id="REQ-X", actor="tester")
    service.close_run(run_id=opened.id, outcome="landed")

    with pytest.raises(ValueError, match="already closed"):
        service.close_run(run_id=opened.id, outcome="bounced")


def test_runs_dir_is_not_inside_gitignored_path(tmp_path: Path) -> None:
    config = MetagitConfig(
        name="demo",
        routing=RoutingConfig(
            catalog="knowledge/requests/entries",
            runs="knowledge/requests/runs",
        ),
    )
    service = RoutingService(config, workspace_root=str(tmp_path))

    assert service.run_store.root == tmp_path / "knowledge/requests/runs"
    assert "/.metagit/" not in service.run_store.root.as_posix()

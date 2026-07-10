#!/usr/bin/env python
"""Unit tests for scheduler JSON store."""

from __future__ import annotations

import json

from metagit.core.scheduler.models import ScheduleDecision, SchedulePolicy, ScheduleWeights
from metagit.core.scheduler.paths import decisions_file, events_file, policy_file, schedule_root
from metagit.core.scheduler.store import ScheduleStore


def test_schedule_paths_resolve_under_metagit_session_root(tmp_path) -> None:
    assert schedule_root(str(tmp_path)) == tmp_path / ".metagit" / "schedule"
    assert policy_file(str(tmp_path)) == tmp_path / ".metagit" / "schedule" / "policy.json"
    assert decisions_file(str(tmp_path)) == tmp_path / ".metagit" / "schedule" / "decisions.jsonl"
    assert events_file(str(tmp_path)) == tmp_path / ".metagit" / "events" / "scheduler.jsonl"


def test_store_returns_default_policy_when_missing(tmp_path) -> None:
    store = ScheduleStore(str(tmp_path))
    policy = store.load_policy()
    assert policy == SchedulePolicy()


def test_store_saves_and_loads_policy(tmp_path) -> None:
    store = ScheduleStore(str(tmp_path))
    policy = SchedulePolicy(weights=ScheduleWeights(priority=2.0, fairness=0.1))
    assert store.save_policy(policy) is None
    loaded = store.load_policy()
    assert loaded == policy
    raw = json.loads(policy_file(str(tmp_path)).read_text(encoding="utf-8"))
    assert raw["weights"]["priority"] == 2.0


def test_store_appends_and_lists_decisions(tmp_path) -> None:
    store = ScheduleStore(str(tmp_path))
    first = ScheduleDecision(
        decision_id="d1",
        at="2026-07-09T00:00:00Z",
        graph_id="g1",
        node_id="n1",
        score=1.5,
        reasons=["priority=1"],
    )
    second = ScheduleDecision(
        decision_id="d2",
        at="2026-07-09T00:01:00Z",
        graph_id="g1",
        node_id="n2",
        score=2.0,
    )
    assert store.append_decision(first) is None
    assert store.append_decision(second) is None
    rows = store.list_decisions()
    assert not isinstance(rows, Exception)
    assert [row.decision_id for row in rows] == ["d1", "d2"]
    limited = store.list_decisions(limit=1)
    assert not isinstance(limited, Exception)
    assert [row.decision_id for row in limited] == ["d2"]

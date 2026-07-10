#!/usr/bin/env python
"""Unit tests for soft merge-queue backpressure."""

from __future__ import annotations

from types import SimpleNamespace

from metagit.core.scheduler.events import ScheduleEventStore
from metagit.core.scheduler.models import SchedulePolicy, ScheduleWeights
from metagit.core.scheduler.service import SchedulerService
from metagit.core.taskgraph.models import TaskNode


def _node(node_id: str, repository: str, *, priority: int = 1) -> TaskNode:
    return TaskNode(
        node_id=node_id,
        graph_id="g1",
        title=node_id,
        status="ready",
        repository=repository,
        priority=priority,
        created_at="2026-07-09T00:00:00Z",
        updated_at="2026-07-09T00:00:00Z",
    )


def test_prefers_repo_without_merge_pressure(tmp_path) -> None:
    ready = [
        _node("pressured", "project/a", priority=10),
        _node("clear", "project/b", priority=1),
    ]
    merges = [
        SimpleNamespace(repository="project/a", status="queued"),
        SimpleNamespace(repository="project/a", status="queued"),
        SimpleNamespace(repository="project/a", status="running"),
    ]
    service = SchedulerService(
        str(tmp_path),
        ready_fn=lambda _gid: ready,
        worktrees_fn=lambda: [],
        merge_status_fn=lambda: merges,
        now_fn=lambda: "2026-07-09T12:00:00Z",
    )
    service.store.save_policy(
        SchedulePolicy(
            weights=ScheduleWeights(affinity=0.0, cost=0.0),
            merge_queue_threshold=3,
            merge_pressure_penalty=20.0,
        )
    )
    decisions = service.next(limit=1)
    assert not isinstance(decisions, Exception)
    assert decisions[0].node_id == "clear"


def test_skip_on_merge_pressure_emits_skipped_decision(tmp_path) -> None:
    ready = [_node("only", "project/a", priority=5)]
    merges = [
        SimpleNamespace(repository="project/a", status="queued"),
        SimpleNamespace(repository="project/a", status="queued"),
        SimpleNamespace(repository="project/a", status="queued"),
    ]
    service = SchedulerService(
        str(tmp_path),
        ready_fn=lambda _gid: ready,
        worktrees_fn=lambda: [],
        merge_status_fn=lambda: merges,
        now_fn=lambda: "2026-07-09T12:00:00Z",
    )
    service.store.save_policy(
        SchedulePolicy(
            weights=ScheduleWeights(affinity=0.0, cost=0.0),
            merge_queue_threshold=3,
            skip_on_merge_pressure=True,
        )
    )
    decisions = service.next(limit=1)
    assert not isinstance(decisions, Exception)
    assert decisions[0].skipped is True
    assert "skipped_due_to_merge_pressure" in decisions[0].reasons
    events = ScheduleEventStore(str(tmp_path)).list_events()
    assert not isinstance(events, Exception)
    assert events[0].type == "ScheduleSkipped"

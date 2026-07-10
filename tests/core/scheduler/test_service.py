#!/usr/bin/env python
"""Unit tests for SchedulerService next/status."""

from __future__ import annotations

from metagit.core.scheduler.events import ScheduleEventStore
from metagit.core.scheduler.models import SchedulePolicy, ScheduleWeights
from metagit.core.scheduler.service import SchedulerService
from metagit.core.scheduler.store import ScheduleStore
from metagit.core.taskgraph.models import TaskAclBinding, TaskNode


def _node(
    node_id: str,
    *,
    priority: int = 0,
    repository: str = "project/repo",
    project: str = "project",
) -> TaskNode:
    return TaskNode(
        node_id=node_id,
        graph_id="g1",
        title=f"Title {node_id}",
        status="ready",
        project=project,
        repository=repository,
        priority=priority,
        acl=TaskAclBinding(acl_commands=["metagit lease acquire --agent demo"]),
        created_at="2026-07-09T00:00:00Z",
        updated_at="2026-07-09T00:00:00Z",
    )


def test_next_picks_higher_priority_and_persists_decision(tmp_path) -> None:
    ready = [_node("low", priority=1), _node("high", priority=9)]
    service = SchedulerService(
        str(tmp_path),
        ready_fn=lambda _gid: ready,
        worktrees_fn=lambda: [],
        merge_status_fn=lambda: [],
        now_fn=lambda: "2026-07-09T12:00:00Z",
    )
    service.store.save_policy(SchedulePolicy(weights=ScheduleWeights(affinity=0.0, cost=0.0)))

    decisions = service.next(limit=1)
    assert not isinstance(decisions, Exception)
    assert len(decisions) == 1
    assert decisions[0].node_id == "high"
    assert decisions[0].skipped is False
    assert "metagit context compile" in (decisions[0].compile_command or "")
    assert decisions[0].acl_commands == ["metagit lease acquire --agent demo"]

    stored = ScheduleStore(str(tmp_path)).list_decisions()
    assert not isinstance(stored, Exception)
    assert stored[0].node_id == "high"

    events = ScheduleEventStore(str(tmp_path)).list_events()
    assert not isinstance(events, Exception)
    assert events[0].type == "ScheduleDecision"


def test_next_returns_empty_when_no_ready_nodes(tmp_path) -> None:
    service = SchedulerService(
        str(tmp_path),
        ready_fn=lambda _gid: [],
        worktrees_fn=lambda: [],
        merge_status_fn=lambda: [],
    )
    decisions = service.next()
    assert decisions == []


def test_status_returns_policy_ready_count_and_recent(tmp_path) -> None:
    service = SchedulerService(
        str(tmp_path),
        ready_fn=lambda _gid: [_node("n1")],
        worktrees_fn=lambda: [],
        merge_status_fn=lambda: [],
        now_fn=lambda: "2026-07-09T12:00:00Z",
    )
    service.next(limit=1)
    status = service.status(recent=5)
    assert not isinstance(status, Exception)
    assert status.ready_count == 1
    assert len(status.recent_decisions) == 1
    assert status.policy.merge_queue_threshold == 3

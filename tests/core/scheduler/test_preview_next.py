#!/usr/bin/env python
"""preview_next must not persist decisions."""

from __future__ import annotations

from metagit.core.scheduler.events import ScheduleEventStore
from metagit.core.scheduler.models import SchedulePolicy, ScheduleWeights
from metagit.core.scheduler.service import SchedulerService
from metagit.core.scheduler.store import ScheduleStore
from metagit.core.taskgraph.models import TaskAclBinding, TaskNode


def _node(node_id: str, *, priority: int = 0) -> TaskNode:
    return TaskNode(
        node_id=node_id,
        graph_id="g1",
        title=f"Title {node_id}",
        status="ready",
        project="project",
        repository="project/repo",
        priority=priority,
        acl=TaskAclBinding(acl_commands=["metagit lease acquire --agent demo"]),
        created_at="2026-07-09T00:00:00Z",
        updated_at="2026-07-09T00:00:00Z",
    )


def test_preview_next_does_not_append_decisions(tmp_path) -> None:
    ready = [_node("n1", priority=5)]
    svc = SchedulerService(
        str(tmp_path),
        ready_fn=lambda _gid: ready,
        worktrees_fn=lambda: [],
        merge_status_fn=lambda: [],
        now_fn=lambda: "2026-07-09T12:00:00Z",
    )
    svc.store.save_policy(SchedulePolicy(weights=ScheduleWeights(affinity=0.0, cost=0.0)))

    preview = svc.preview_next(limit=1)
    assert not isinstance(preview, Exception)
    assert len(preview) == 1
    assert preview[0].node_id == "n1"

    listed = ScheduleStore(str(tmp_path)).list_decisions()
    assert not isinstance(listed, Exception)
    assert listed == []

    events = ScheduleEventStore(str(tmp_path)).list_events()
    assert not isinstance(events, Exception)
    assert events == []

    committed = svc.next(limit=1)
    assert not isinstance(committed, Exception)
    listed2 = ScheduleStore(str(tmp_path)).list_decisions()
    assert not isinstance(listed2, Exception)
    assert len(listed2) == 1

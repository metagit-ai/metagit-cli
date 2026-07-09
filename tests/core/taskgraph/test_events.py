#!/usr/bin/env python
"""Tests for taskgraph event emission and workspace event merge."""

from __future__ import annotations

from pathlib import Path

from metagit.core.context.event_service import WorkspaceEventService
from metagit.core.taskgraph.service import TaskGraphService


def test_complete_emits_taskgraph_events(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    service = TaskGraphService(str(session))
    graph = service.create(title="Events", goal="emit")
    assert not isinstance(graph, Exception)
    expanded = service.expand(
        graph.graph_id,
        [{"node_id": "root", "title": "Root"}],
    )
    assert not isinstance(expanded, Exception)
    completed = service.complete("root", graph_id=graph.graph_id)
    assert not isinstance(completed, Exception)

    feed = WorkspaceEventService(str(session)).list_events()
    kinds = {(e.source, e.kind) for e in feed.events}
    assert ("taskgraph", "TaskGraphCreated") in kinds
    assert ("taskgraph", "TaskNodeCreated") in kinds
    assert ("taskgraph", "TaskCompleted") in kinds

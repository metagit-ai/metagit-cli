#!/usr/bin/env python
"""Unit tests for TaskGraphStore."""

from __future__ import annotations

from pathlib import Path

from metagit.core.taskgraph.models import TaskGraph, TaskNode
from metagit.core.taskgraph.paths import graph_file, tasks_root
from metagit.core.taskgraph.store import TaskGraphStore


def test_store_round_trip(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    store = TaskGraphStore(str(session))
    graph = TaskGraph(
        graph_id="g1",
        title="Round trip",
        nodes=[
            TaskNode(
                node_id="n1",
                graph_id="g1",
                title="A",
                created_at="2026-07-09T00:00:00+00:00",
                updated_at="2026-07-09T00:00:00+00:00",
            )
        ],
        created_at="2026-07-09T00:00:00+00:00",
        updated_at="2026-07-09T00:00:00+00:00",
    )
    err = store.save(graph)
    assert err is None
    assert graph_file(str(session), "g1").is_file()
    assert tasks_root(str(session)).is_dir()
    loaded = store.load("g1")
    assert not isinstance(loaded, Exception)
    assert loaded.title == "Round trip"
    assert loaded.nodes[0].node_id == "n1"
    listed = store.list_graphs()
    assert not isinstance(listed, Exception)
    assert len(listed) == 1

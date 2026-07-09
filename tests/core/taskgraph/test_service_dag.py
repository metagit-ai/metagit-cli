#!/usr/bin/env python
"""DAG ready-set and cycle detection tests for TaskGraphService."""

from __future__ import annotations

from pathlib import Path

from metagit.core.taskgraph.service import TaskGraphService, compute_ready_ids, detect_cycle
from metagit.core.taskgraph.models import TaskNode


def _node(node_id: str, deps: list[str] | None = None, status: str = "pending") -> TaskNode:
    return TaskNode(
        node_id=node_id,
        graph_id="g",
        title=node_id,
        depends_on=list(deps or []),
        status=status,  # type: ignore[arg-type]
        created_at="2026-07-09T00:00:00+00:00",
        updated_at="2026-07-09T00:00:00+00:00",
    )


def test_detect_cycle() -> None:
    nodes = [_node("a", ["b"]), _node("b", ["a"])]
    assert detect_cycle(nodes) is not None
    assert detect_cycle([_node("a"), _node("b", ["a"])]) is None


def test_compute_ready_diamond() -> None:
    nodes = [
        _node("root"),
        _node("left", ["root"]),
        _node("right", ["root"]),
        _node("merge", ["left", "right"]),
    ]
    assert compute_ready_ids(nodes) == {"root"}
    nodes[0].status = "completed"
    assert compute_ready_ids(nodes) == {"left", "right"}
    nodes[1].status = "completed"
    nodes[2].status = "completed"
    assert compute_ready_ids(nodes) == {"merge"}


def test_service_expand_ready_complete(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    service = TaskGraphService(str(session))
    graph = service.create(title="Demo", goal="Ship DAG")
    assert not isinstance(graph, Exception)
    expanded = service.expand(
        graph.graph_id,
        [
            {"node_id": "root", "title": "Root"},
            {"node_id": "child", "title": "Child", "depends_on": ["root"]},
            {"node_id": "leaf", "title": "Leaf", "depends_on": ["child"]},
        ],
    )
    assert not isinstance(expanded, Exception)
    ready = service.ready(graph.graph_id)
    assert not isinstance(ready, Exception)
    assert [n.node_id for n in ready] == ["root"]
    completed = service.complete("root", graph_id=graph.graph_id)
    assert not isinstance(completed, Exception)
    ready2 = service.ready(graph.graph_id)
    assert not isinstance(ready2, Exception)
    assert [n.node_id for n in ready2] == ["child"]


def test_service_rejects_cycle(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    service = TaskGraphService(str(session))
    graph = service.create(title="Cycle", goal="fail")
    assert not isinstance(graph, Exception)
    result = service.expand(
        graph.graph_id,
        [
            {"node_id": "a", "title": "A", "depends_on": ["b"]},
            {"node_id": "b", "title": "B", "depends_on": ["a"]},
        ],
    )
    assert isinstance(result, Exception)


def test_outline_indent_expand(tmp_path: Path) -> None:
    session = tmp_path / "session"
    session.mkdir()
    service = TaskGraphService(str(session))
    graph = service.create(title="Outline", goal="indent")
    assert not isinstance(graph, Exception)
    outline = "Root\n  Child\n    Leaf\n"
    expanded = service.expand(graph.graph_id, outline)
    assert not isinstance(expanded, Exception)
    by_id = {n.node_id: n for n in expanded.nodes}
    assert "root" in by_id
    assert by_id["child"].depends_on == ["root"]
    assert by_id["leaf"].depends_on == ["child"]

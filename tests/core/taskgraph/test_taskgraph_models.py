#!/usr/bin/env python
"""Unit tests for taskgraph models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from metagit.core.taskgraph.models import TaskGraph, TaskNode


def test_task_node_rejects_invalid_id() -> None:
    with pytest.raises(ValidationError):
        TaskNode(
            node_id="bad id!",
            graph_id="g1",
            title="x",
            created_at="2026-07-09T00:00:00+00:00",
            updated_at="2026-07-09T00:00:00+00:00",
        )


def test_task_graph_round_trip_fields() -> None:
    graph = TaskGraph(
        graph_id="graph-1",
        title="Demo",
        nodes=[
            TaskNode(
                node_id="n1",
                graph_id="graph-1",
                title="Root",
                status="ready",
                created_at="2026-07-09T00:00:00+00:00",
                updated_at="2026-07-09T00:00:00+00:00",
            )
        ],
        created_at="2026-07-09T00:00:00+00:00",
        updated_at="2026-07-09T00:00:00+00:00",
    )
    dumped = graph.model_dump(mode="json")
    restored = TaskGraph.model_validate(dumped)
    assert restored.graph_id == "graph-1"
    assert restored.nodes[0].status == "ready"

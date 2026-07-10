#!/usr/bin/env python
"""CLI tests for schedule commands (RFC-0012)."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli
from metagit.core.taskgraph.models import TaskNode
from metagit.core.taskgraph.service import TaskGraphService


_WORKSPACE_YML = "\n".join(
    [
        "name: workspace",
        "kind: application",
        "workspace:",
        "  projects:",
        "    - name: alpha",
        "      repos: []",
    ]
)


def _seed_ready_graph(root: Path) -> None:
    service = TaskGraphService(str(root))
    graph = service.create(title="Demo", goal="Ship", graph_id="g1")
    assert not isinstance(graph, Exception)
    now = "2026-07-09T00:00:00Z"
    graph.nodes = [
        TaskNode(
            node_id="low",
            graph_id="g1",
            title="Low",
            status="ready",
            project="alpha",
            repository="alpha/repo",
            priority=1,
            created_at=now,
            updated_at=now,
        ),
        TaskNode(
            node_id="high",
            graph_id="g1",
            title="High",
            status="ready",
            project="alpha",
            repository="alpha/repo",
            priority=9,
            created_at=now,
            updated_at=now,
        ),
    ]
    assert service._store.save(graph) is None  # noqa: SLF001 — test fixture


def test_schedule_policy_show_and_next_json(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
    _seed_ready_graph(tmp_path)
    runner = CliRunner()

    show = runner.invoke(
        cli,
        ["schedule", "policy", "show", "--definition", str(tmp_path / ".metagit.yml"), "--json"],
    )
    assert show.exit_code == 0, show.output
    policy = json.loads(show.output)
    assert policy["weights"]["priority"] == 1.0

    nxt = runner.invoke(
        cli,
        [
            "schedule",
            "next",
            "--definition",
            str(tmp_path / ".metagit.yml"),
            "--limit",
            "1",
            "--json",
        ],
    )
    assert nxt.exit_code == 0, nxt.output
    decisions = json.loads(nxt.output)
    assert decisions[0]["node_id"] == "high"

    status = runner.invoke(
        cli,
        ["schedule", "status", "--definition", str(tmp_path / ".metagit.yml"), "--json"],
    )
    assert status.exit_code == 0, status.output
    payload = json.loads(status.output)
    assert payload["ready_count"] == 2
    assert len(payload["recent_decisions"]) == 1

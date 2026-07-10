#!/usr/bin/env python
"""MCP tests for schedule tools (RFC-0012)."""

from __future__ import annotations

import json
from pathlib import Path

from metagit.core.mcp.runtime import MetagitMcpRuntime
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


def _payload(response: dict) -> object:
    return json.loads(response["result"]["content"][0]["text"])


def _seed_ready_graph(root: Path) -> None:
    service = TaskGraphService(str(root))
    graph = service.create(title="Demo", goal="Ship", graph_id="g1")
    assert not isinstance(graph, Exception)
    now = "2026-07-09T00:00:00Z"
    graph.nodes = [
        TaskNode(
            node_id="n1",
            graph_id="g1",
            title="One",
            status="ready",
            project="alpha",
            repository="alpha/repo",
            priority=3,
            created_at=now,
            updated_at=now,
        )
    ]
    assert service._store.save(graph) is None  # noqa: SLF001 — test fixture


def test_tools_list_includes_schedule_tools(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 800, "method": "tools/list", "params": {}}
    )
    assert response is not None
    names = [item["name"] for item in response["result"]["tools"]]
    assert "metagit_schedule_next" in names
    assert "metagit_schedule_status" in names
    assert "metagit_schedule_policy" in names


def test_tools_call_schedule_policy_and_next(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
    _seed_ready_graph(tmp_path)
    runtime = MetagitMcpRuntime(root=str(tmp_path))

    policy = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 801,
            "method": "tools/call",
            "params": {
                "name": "metagit_schedule_policy",
                "arguments": {"action": "set", "priority": 2.0},
            },
        }
    )
    assert policy is not None
    assert _payload(policy)["weights"]["priority"] == 2.0

    nxt = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 802,
            "method": "tools/call",
            "params": {"name": "metagit_schedule_next", "arguments": {"limit": 1}},
        }
    )
    assert nxt is not None
    decisions = _payload(nxt)
    assert isinstance(decisions, list)
    assert decisions[0]["node_id"] == "n1"

    status = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 803,
            "method": "tools/call",
            "params": {"name": "metagit_schedule_status", "arguments": {}},
        }
    )
    assert status is not None
    payload = _payload(status)
    assert payload["ready_count"] == 1

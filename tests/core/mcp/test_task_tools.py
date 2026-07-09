#!/usr/bin/env python
"""MCP tests for task graph tools (RFC-0008)."""

from __future__ import annotations

import json
from pathlib import Path

from metagit.core.mcp.runtime import MetagitMcpRuntime

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


def test_tools_list_includes_task_tools(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 500, "method": "tools/list", "params": {}}
    )
    assert response is not None
    names = [item["name"] for item in response["result"]["tools"]]
    assert "metagit_task_create" in names
    assert "metagit_task_expand" in names
    assert "metagit_task_ready" in names
    assert "metagit_task_complete" in names
    assert "metagit_task_bind_acl" in names


def test_tools_call_task_create_expand_ready(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    create = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 501,
            "method": "tools/call",
            "params": {
                "name": "metagit_task_create",
                "arguments": {
                    "title": "MCP graph",
                    "goal": "ready set",
                    "graph_id": "mcp-g1",
                },
            },
        }
    )
    assert create is not None
    created = json.loads(create["result"]["content"][0]["text"])
    assert created["graph_id"] == "mcp-g1"

    expand = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 502,
            "method": "tools/call",
            "params": {
                "name": "metagit_task_expand",
                "arguments": {
                    "graph_id": "mcp-g1",
                    "outline": [
                        {"node_id": "root", "title": "Root"},
                        {"node_id": "child", "title": "Child", "depends_on": ["root"]},
                    ],
                },
            },
        }
    )
    assert expand is not None
    ready = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 503,
            "method": "tools/call",
            "params": {
                "name": "metagit_task_ready",
                "arguments": {"graph_id": "mcp-g1"},
            },
        }
    )
    assert ready is not None
    payload = json.loads(ready["result"]["content"][0]["text"])
    assert payload["ok"] is True
    assert [item["node_id"] for item in payload["items"]] == ["root"]


def test_tools_list_includes_context_compile(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 510, "method": "tools/list", "params": {}}
    )
    assert response is not None
    names = [item["name"] for item in response["result"]["tools"]]
    assert "metagit_context_compile" in names


def test_tools_call_context_compile(tmp_path: Path) -> None:
    from git import Repo

    repo_dir = tmp_path / "alpha" / "svc"
    repo_dir.mkdir(parents=True)
    Repo.init(repo_dir)
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: alpha",
                "      repos:",
                "        - name: svc",
                "          path: alpha/svc",
                "          sync: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 511,
            "method": "tools/call",
            "params": {
                "name": "metagit_context_compile",
                "arguments": {
                    "project_name": "alpha",
                    "repo_name": "svc",
                    "tier": 1,
                    "budget": 20000,
                },
            },
        }
    )
    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["ok"] is True
    assert payload["inputs"]["project"] == "alpha"
    assert Path(payload["artifact_path"]).is_file()

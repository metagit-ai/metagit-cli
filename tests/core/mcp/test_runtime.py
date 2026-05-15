#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.runtime
"""

import json
from pathlib import Path

from metagit.core.mcp.runtime import MetagitMcpRuntime


def test_initialize_request_returns_capabilities(tmp_path: Path) -> None:
    runtime = MetagitMcpRuntime(root=str(tmp_path))

    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )

    assert response is not None
    assert response["result"]["serverInfo"]["name"] == "metagit-mcp"
    assert "tools" in response["result"]["capabilities"]


def test_tools_list_returns_inactive_tools_without_config(tmp_path: Path) -> None:
    runtime = MetagitMcpRuntime(root=str(tmp_path))

    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    )

    assert response is not None
    names = [item["name"] for item in response["result"]["tools"]]
    assert "metagit_workspace_status" in names
    assert "metagit_bootstrap_config_plan_only" in names
    assert "metagit_workspace_index" not in names
    workspace_status_tool = next(
        item for item in response["result"]["tools"] if item["name"] == "metagit_workspace_status"
    )
    assert workspace_status_tool["inputSchema"]["type"] == "object"


def test_tools_call_workspace_status_returns_text_payload(tmp_path: Path) -> None:
    runtime = MetagitMcpRuntime(root=str(tmp_path))

    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "metagit_workspace_status", "arguments": {}},
        }
    )

    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["state"] == "inactive_missing_config"


def test_resources_read_ops_log_returns_json_content(tmp_path: Path) -> None:
    runtime = MetagitMcpRuntime(root=str(tmp_path))

    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/read",
            "params": {"uri": "metagit://workspace/ops-log"},
        }
    )

    assert response is not None
    assert response["result"]["contents"][0]["mimeType"] == "application/json"


def test_tools_call_invalid_arguments_returns_mcp_invalid_params(tmp_path: Path) -> None:
    runtime = MetagitMcpRuntime(root=str(tmp_path))

    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "metagit_workspace_search", "arguments": {}},
        }
    )

    assert response is not None
    assert response["error"]["code"] == -32602
    assert response["error"]["data"]["kind"] == "invalid_arguments"


def test_tools_call_workspace_semantic_search_requires_query(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: default",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {
                "name": "metagit_workspace_semantic_search",
                "arguments": {"query": "  "},
            },
        }
    )

    assert response is not None
    assert response["error"]["code"] == -32602
    assert response["error"]["data"]["kind"] == "invalid_arguments"


def test_initialize_can_enable_sampling_capability(tmp_path: Path) -> None:
    runtime = MetagitMcpRuntime(root=str(tmp_path))

    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "initialize",
            "params": {"capabilities": {"sampling": {}}},
        }
    )

    assert response is not None
    assert runtime._sampling_supported is True


def test_bootstrap_uses_sampling_when_client_supports_it(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: sampled-workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: default",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    runtime._sampling_supported = True
    runtime._request_client_sampling = lambda context: {  # type: ignore[method-assign]
        "content": {
            "type": "text",
            "text": "\n".join(
                [
                    "name: sampled",
                    "kind: application",
                    "workspace:",
                    "  projects:",
                    "    - name: default",
                    "      repos: []",
                ]
            )
            + "\n",
        }
    }

    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "metagit_bootstrap_config", "arguments": {}},
        }
    )

    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["mode"] == "sampled"


def test_tools_list_includes_repo_search_for_active_workspace(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: platform",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 10, "method": "tools/list", "params": {}}
    )

    assert response is not None
    names = [item["name"] for item in response["result"]["tools"]]
    assert "metagit_repo_search" in names


def test_tools_call_repo_search_returns_matches(tmp_path: Path) -> None:
    repo_dir = tmp_path / "platform" / "abacus-app"
    repo_dir.mkdir(parents=True)
    (repo_dir / ".git").mkdir()
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: platform",
                "      repos:",
                "        - name: abacus-app",
                "          path: platform/abacus-app",
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
            "id": 11,
            "method": "tools/call",
            "params": {"name": "metagit_repo_search", "arguments": {"query": "abacus"}},
        }
    )

    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["matches"][0]["repo_name"] == "abacus-app"


def test_tools_list_includes_project_context_tools(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: alpha",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 20, "method": "tools/list", "params": {}}
    )

    assert response is not None
    names = [item["name"] for item in response["result"]["tools"]]
    assert "metagit_project_context_switch" in names
    assert "metagit_workspace_state_snapshot" in names


def test_tools_call_project_context_switch_unknown_project(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: alpha",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 21,
            "method": "tools/call",
            "params": {
                "name": "metagit_project_context_switch",
                "arguments": {"project_name": "missing"},
            },
        }
    )

    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["ok"] is False
    assert payload["error"] == "project_not_found"


def test_tools_call_cross_project_dependencies(tmp_path: Path) -> None:
    (tmp_path / "alpha" / "api").mkdir(parents=True)
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: alpha",
                "      repos:",
                "        - name: api",
                "          path: alpha/api",
                "          sync: true",
                "    - name: beta",
                "      repos:",
                "        - name: worker",
                "          path: beta/worker",
                "          sync: true",
                "          tags:",
                "            depends_on: alpha",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 30,
            "method": "tools/call",
            "params": {
                "name": "metagit_cross_project_dependencies",
                "arguments": {
                    "source_project": "alpha",
                    "dependency_types": ["declared"],
                    "depth": 2,
                },
            },
        }
    )

    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["ok"] is True
    assert payload["source_project"] == "alpha"

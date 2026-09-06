#!/usr/bin/env python
"""MCP tests for component list/show/resolve tools (RFC-0027)."""

from __future__ import annotations

import json
from pathlib import Path

from metagit.core.mcp.runtime import MetagitMcpRuntime

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "components"
NATIVE = FIXTURES / "native-nested.yml"

_COMPONENT_TOOLS = (
    "metagit_component_list",
    "metagit_component_show",
    "metagit_component_resolve",
    "metagit_component_graph",
)


def _payload(response: dict) -> object:
    return json.loads(response["result"]["content"][0]["text"])


def _seed(tmp_path: Path) -> MetagitMcpRuntime:
    (tmp_path / ".metagit.yml").write_text(NATIVE.read_text(encoding="utf-8"), encoding="utf-8")
    return MetagitMcpRuntime(root=str(tmp_path))


def _call(runtime: MetagitMcpRuntime, name: str, arguments: dict, request_id: int) -> dict:
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )
    assert response is not None
    return response


def test_tools_list_includes_component_tools(tmp_path: Path) -> None:
    runtime = _seed(tmp_path)
    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 920, "method": "tools/list", "params": {}}
    )
    assert response is not None
    tools = {item["name"]: item for item in response["result"]["tools"]}
    for name in _COMPONENT_TOOLS:
        assert name in tools
        schema = tools[name]["inputSchema"]
        assert schema.get("additionalProperties") is False


def test_component_schemas_require_expected_fields(tmp_path: Path) -> None:
    runtime = _seed(tmp_path)
    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 921, "method": "tools/list", "params": {}}
    )
    assert response is not None
    tools = {item["name"]: item for item in response["result"]["tools"]}
    list_schema = tools["metagit_component_list"]["inputSchema"]
    show_schema = tools["metagit_component_show"]["inputSchema"]
    resolve_schema = tools["metagit_component_resolve"]["inputSchema"]
    assert set(list_schema["properties"]) == {"project", "repo"}
    assert "required" not in list_schema or list_schema.get("required") == []
    assert show_schema["required"] == ["component"]
    assert set(show_schema["properties"]) == {"component", "project", "repo"}
    assert resolve_schema["required"] == ["path"]
    assert set(resolve_schema["properties"]) == {"path", "project", "repo"}
    graph_schema = tools["metagit_component_graph"]["inputSchema"]
    assert graph_schema["required"] == ["component"]
    assert set(graph_schema["properties"]) == {
        "component",
        "project",
        "repo",
        "depth",
        "direction",
    }


def test_component_list_includes_nested_web(tmp_path: Path) -> None:
    runtime = _seed(tmp_path)
    response = _call(runtime, "metagit_component_list", {}, 922)
    payload = _payload(response)
    assert isinstance(payload, dict)
    ids = {row["id"] for row in payload["components"]}
    assert "platform/core/web" in ids


def test_component_show_returns_web(tmp_path: Path) -> None:
    runtime = _seed(tmp_path)
    response = _call(
        runtime,
        "metagit_component_show",
        {"component": "platform/core/web"},
        923,
    )
    payload = _payload(response)
    assert isinstance(payload, dict)
    assert payload["id"] == "platform/core/web"
    assert payload["name"] == "web"
    assert payload["path"] == "apps/web"


def test_component_resolve_matches_web(tmp_path: Path) -> None:
    runtime = _seed(tmp_path)
    query = "apps/web/src/login.tsx"
    response = _call(
        runtime,
        "metagit_component_resolve",
        {"path": query, "project": "platform", "repo": "core"},
        924,
    )
    payload = _payload(response)
    assert isinstance(payload, dict)
    assert payload["matched"] is True
    assert payload["path"] == query
    assert payload["name"] == "web"
    assert payload["spec"]["path"] == "apps/web"


def test_component_resolve_miss_is_success(tmp_path: Path) -> None:
    runtime = _seed(tmp_path)
    query = "docs/nope.md"
    response = _call(
        runtime,
        "metagit_component_resolve",
        {"path": query, "project": "platform", "repo": "core"},
        925,
    )
    assert "error" not in response
    payload = _payload(response)
    assert isinstance(payload, dict)
    assert payload["matched"] is False
    assert payload["path"] == query


def test_component_graph_returns_nodes_and_edges(tmp_path: Path) -> None:
    runtime = _seed(tmp_path)
    response = _call(
        runtime,
        "metagit_component_graph",
        {"component": "platform/core/web"},
        930,
    )
    payload = _payload(response)
    assert isinstance(payload, dict)
    assert payload["origin"]["id"] == "platform/core/web"
    assert payload["nodes"]
    assert payload["edges"]
    neighbor_ids = {row["id"] for row in payload["nodes"]}
    assert "platform/core/api" in neighbor_ids


def test_component_graph_not_found_is_invalid_arguments(tmp_path: Path) -> None:
    runtime = _seed(tmp_path)
    response = _call(
        runtime,
        "metagit_component_graph",
        {"component": "missing-nope"},
        931,
    )
    assert response["error"]["code"] == -32602
    assert response["error"]["data"]["kind"] == "invalid_arguments"


def test_component_show_not_found_is_invalid_arguments(tmp_path: Path) -> None:
    runtime = _seed(tmp_path)
    response = _call(
        runtime,
        "metagit_component_show",
        {"component": "platform/core/missing"},
        926,
    )
    assert response["error"]["code"] == -32602
    assert response["error"]["data"]["kind"] == "invalid_arguments"


def test_component_resolve_invalid_path_is_invalid_arguments(tmp_path: Path) -> None:
    runtime = _seed(tmp_path)
    response = _call(
        runtime,
        "metagit_component_resolve",
        {"path": "../escape", "project": "platform", "repo": "core"},
        927,
    )
    assert response["error"]["code"] == -32602
    assert response["error"]["data"]["kind"] == "invalid_arguments"


def test_component_tools_require_active_workspace(tmp_path: Path) -> None:
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    listed = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 928, "method": "tools/list", "params": {}}
    )
    assert listed is not None
    names = [item["name"] for item in listed["result"]["tools"]]
    for name in _COMPONENT_TOOLS:
        assert name not in names
    response = _call(runtime, "metagit_component_list", {}, 929)
    assert response["error"]["code"] == -32602
    assert response["error"]["data"]["kind"] == "invalid_arguments"

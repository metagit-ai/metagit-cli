#!/usr/bin/env python
"""MCP tests for aos/coord tools (RFC-0013)."""

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


def _payload(response: dict) -> object:
    return json.loads(response["result"]["content"][0]["text"])


def test_tools_list_includes_aos_and_coord(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {"jsonrpc": "2.0", "id": 900, "method": "tools/list", "params": {}}
    )
    assert response is not None
    names = [item["name"] for item in response["result"]["tools"]]
    for name in (
        "metagit_aos_status",
        "metagit_aos_doctor",
        "metagit_aos_next",
        "metagit_coord_status",
        "metagit_coord_doctor",
        "metagit_coord_next",
    ):
        assert name in names


def test_aos_and_coord_status_same_shape(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    aos = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 901,
            "method": "tools/call",
            "params": {"name": "metagit_aos_status", "arguments": {}},
        }
    )
    coord = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 902,
            "method": "tools/call",
            "params": {"name": "metagit_coord_status", "arguments": {}},
        }
    )
    assert aos is not None and coord is not None
    aos_payload = _payload(aos)
    coord_payload = _payload(coord)
    assert isinstance(aos_payload, dict) and isinstance(coord_payload, dict)
    assert "subsystems" in aos_payload
    assert set(aos_payload["subsystems"]) == set(coord_payload["subsystems"])


def test_aos_doctor_fix_without_confirm_errors(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 903,
            "method": "tools/call",
            "params": {
                "name": "metagit_aos_doctor",
                "arguments": {"fix": True, "confirm": False},
            },
        }
    )
    assert response is not None
    assert "error" in response or (
        isinstance(response.get("result"), dict)
        and response["result"].get("isError")
    )

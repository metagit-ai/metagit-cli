#!/usr/bin/env python
"""MCP tests for semantic ownership tools (RFC-0010)."""

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


def test_tools_list_includes_semantic_tools(tmp_path: Path) -> None:
  (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
  runtime = MetagitMcpRuntime(root=str(tmp_path))
  response = runtime._handle_request(
    {"jsonrpc": "2.0", "id": 600, "method": "tools/list", "params": {}}
  )
  assert response is not None
  names = [item["name"] for item in response["result"]["tools"]]
  assert "metagit_semantic_declare" in names
  assert "metagit_semantic_query" in names
  assert "metagit_semantic_owners" in names
  assert "metagit_semantic_conflicts" in names
  assert "metagit_semantic_ingest" in names


def test_tools_call_semantic_declare_query_owners(tmp_path: Path) -> None:
  (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
  runtime = MetagitMcpRuntime(root=str(tmp_path))
  declare = runtime._handle_request(
    {
      "jsonrpc": "2.0",
      "id": 601,
      "method": "tools/call",
      "params": {
        "name": "metagit_semantic_declare",
        "arguments": {
          "concept": "Authentication",
          "repository": "alpha/api",
          "patterns": ["src/auth/**"],
        },
      },
    }
  )
  assert declare is not None
  declared = json.loads(declare["result"]["content"][0]["text"])
  assert declared["ok"] is True
  assert declared["concept"]["concept_id"] == "authentication"
  assert declared["ownership"]["repository"] == "alpha/api"

  query = runtime._handle_request(
    {
      "jsonrpc": "2.0",
      "id": 602,
      "method": "tools/call",
      "params": {
        "name": "metagit_semantic_query",
        "arguments": {"concept": "authentication"},
      },
    }
  )
  assert query is not None
  queried = json.loads(query["result"]["content"][0]["text"])
  assert queried["ok"] is True
  assert queried["concept"]["name"] == "Authentication"
  assert [item["repository"] for item in queried["ownerships"]] == ["alpha/api"]

  owners = runtime._handle_request(
    {
      "jsonrpc": "2.0",
      "id": 603,
      "method": "tools/call",
      "params": {
        "name": "metagit_semantic_owners",
        "arguments": {
          "repository": "alpha/api",
          "path": "src/auth/login.py",
        },
      },
    }
  )
  assert owners is not None
  payload = json.loads(owners["result"]["content"][0]["text"])
  assert payload["ok"] is True
  assert [item["concept_id"] for item in payload["concepts"]] == ["authentication"]

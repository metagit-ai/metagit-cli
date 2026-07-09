#!/usr/bin/env python
"""MCP tests for merge orchestrator tools (RFC-0011)."""

from __future__ import annotations

import json
from pathlib import Path

from git import Repo

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


def _commit_file(repo: Repo, relative_path: str, content: str, message: str) -> str:
  path = Path(repo.working_tree_dir or "") / relative_path
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(content, encoding="utf-8")
  repo.index.add([relative_path])
  return repo.index.commit(message).hexsha


def _repo(path: Path) -> Repo:
  repo = Repo.init(path)
  with repo.config_writer() as writer:
    writer.set_value("user", "name", "Metagit Test")
    writer.set_value("user", "email", "metagit@example.test")
  _commit_file(repo, "README.md", "base\n", "initial commit")
  repo.create_head("main")
  repo.head.reference = repo.heads.main
  repo.head.reset(index=True, working_tree=True)
  repo.create_head("agent/change", repo.heads.main)
  repo.head.reference = repo.heads["agent/change"]
  repo.head.reset(index=True, working_tree=True)
  _commit_file(repo, "feature.txt", "feature\n", "add feature")
  repo.create_head("integration/test", repo.heads.main)
  repo.head.reference = repo.heads.main
  repo.head.reset(index=True, working_tree=True)
  return repo


def _payload(response: dict) -> dict:
  return json.loads(response["result"]["content"][0]["text"])


def test_tools_list_includes_merge_tools(tmp_path: Path) -> None:
  (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
  runtime = MetagitMcpRuntime(root=str(tmp_path))
  response = runtime._handle_request(
    {"jsonrpc": "2.0", "id": 700, "method": "tools/list", "params": {}}
  )
  assert response is not None
  names = [item["name"] for item in response["result"]["tools"]]
  assert "metagit_merge_enqueue" in names
  assert "metagit_merge_status" in names
  assert "metagit_merge_retry" in names
  assert "metagit_merge_integrate" in names


def test_tools_call_merge_enqueue_integrate_status(tmp_path: Path) -> None:
  (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
  repo_path = tmp_path / "repo"
  _repo(repo_path)
  runtime = MetagitMcpRuntime(root=str(tmp_path))

  enqueue = runtime._handle_request(
    {
      "jsonrpc": "2.0",
      "id": 701,
      "method": "tools/call",
      "params": {
        "name": "metagit_merge_enqueue",
        "arguments": {
          "repository": "alpha/repo",
          "source_branch": "agent/change",
          "target_branch": "integration/test",
          "repo_path": str(repo_path),
        },
      },
    }
  )
  assert enqueue is not None
  queued = _payload(enqueue)
  assert queued["status"] == "queued"

  integrate = runtime._handle_request(
    {
      "jsonrpc": "2.0",
      "id": 702,
      "method": "tools/call",
      "params": {
        "name": "metagit_merge_integrate",
        "arguments": {"merge_id": queued["merge_id"]},
      },
    }
  )
  assert integrate is not None
  integrated = _payload(integrate)
  assert integrated["status"] == "succeeded"

  status = runtime._handle_request(
    {
      "jsonrpc": "2.0",
      "id": 703,
      "method": "tools/call",
      "params": {
        "name": "metagit_merge_status",
        "arguments": {"repository": "alpha/repo"},
      },
    }
  )
  assert status is not None
  payload = _payload(status)
  assert payload["ok"] is True
  assert [item["merge_id"] for item in payload["items"]] == [queued["merge_id"]]

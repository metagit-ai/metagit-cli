#!/usr/bin/env python
"""MCP tests for paged campaign status and board-sync."""

from __future__ import annotations

import json
from pathlib import Path

from metagit.core.campaign.service import CampaignService
from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.runtime import MetagitMcpRuntime
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _workspace(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: demo",
                "      repos:",
                "        - name: alpha",
                "          url: https://github.com/org/alpha.git",
                "        - name: beta",
                "          url: https://github.com/org/beta.git",
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    config = MetagitConfig(
        name="workspace",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="demo",
                    repos=[
                        ProjectPath(name="alpha", url="https://github.com/org/alpha.git"),
                        ProjectPath(name="beta", url="https://github.com/org/beta.git"),
                    ],
                ),
            ],
        ),
    )
    CampaignService(config=config, definition_root=tmp_path).create(
        slug="rollout",
        title="Rollout",
        repos=["demo/alpha", "demo/beta"],
    )


def test_tools_list_includes_campaign_reduction_tools(tmp_path: Path) -> None:
    _workspace(tmp_path)
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request({"jsonrpc": "2.0", "id": 20, "method": "tools/list", "params": {}})
    assert response is not None
    names = [item["name"] for item in response["result"]["tools"]]
    assert "metagit_campaign_status" in names
    assert "metagit_campaign_board_sync" in names


def test_tools_call_campaign_status_pages_repos(tmp_path: Path) -> None:
    _workspace(tmp_path)
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 21,
            "method": "tools/call",
            "params": {
                "name": "metagit_campaign_status",
                "arguments": {"campaign": "rollout", "limit": 1, "offset": 0},
            },
        },
    )
    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["repo_count"] == 2
    assert payload["truncated"] is True
    assert len(payload["repos"]) == 1
    assert "selection" not in payload


def test_tools_call_campaign_board_sync_dry_run(tmp_path: Path) -> None:
    _workspace(tmp_path)
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 22,
            "method": "tools/call",
            "params": {
                "name": "metagit_campaign_board_sync",
                "arguments": {
                    "campaign": "rollout",
                    "organization": "org",
                    "project": "platform",
                    "dry_run": True,
                    "limit": 1,
                },
            },
        },
    )
    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["truncated"] is True
    assert payload["matched_count"] == 2


def test_tools_call_campaign_board_sync_requires_token_when_not_dry_run(tmp_path: Path) -> None:
    _workspace(tmp_path)
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 23,
            "method": "tools/call",
            "params": {
                "name": "metagit_campaign_board_sync",
                "arguments": {
                    "campaign": "rollout",
                    "organization": "org",
                    "project": "platform",
                },
            },
        },
    )
    assert response is not None
    assert response["error"]["code"] == -32602

#!/usr/bin/env python
"""MCP tests for metagit_campaign_context."""

from __future__ import annotations

import json
from pathlib import Path

from metagit.core.campaign.service import CampaignService
from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.runtime import MetagitMcpRuntime
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject
from tests.core.integrations.everroom.mock_gateway import SECRET_TOKEN


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
                "        - name: terraform-network",
                "          url: https://github.com/org/terraform-network.git",
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
                    repos=[ProjectPath(name="terraform-network", url="https://github.com/org/terraform-network.git")],
                ),
            ],
        ),
    )
    CampaignService(config=config, definition_root=tmp_path).create(
        slug="terraform-hcp-migration",
        title="HCP migration",
        repos=["demo/terraform-network"],
        goal="Migrate Terraform from HCP to self-hosted",
    )


def test_tools_list_includes_campaign_context(tmp_path: Path) -> None:
    _workspace(tmp_path)
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request({"jsonrpc": "2.0", "id": 10, "method": "tools/list", "params": {}})
    assert response is not None
    names = [item["name"] for item in response["result"]["tools"]]
    assert "metagit_campaign_context" in names
    tool = next(item for item in response["result"]["tools"] if item["name"] == "metagit_campaign_context")
    assert tool["inputSchema"]["required"] == ["campaign"]


def test_tools_call_campaign_context(tmp_path: Path) -> None:
    _workspace(tmp_path)
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "metagit_campaign_context",
                "arguments": {
                    "campaign": "terraform-hcp-migration",
                    "include": ["summary", "repositories", "decisions"],
                },
            },
        },
    )
    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["campaign"]["id"] == "terraform-hcp-migration"
    assert payload["context_schema_version"] == "1"
    assert payload["everroom"]["status"] == "NOT_CONFIGURED"
    assert SECRET_TOKEN not in json.dumps(payload)


def test_tools_call_campaign_context_requires_campaign(tmp_path: Path) -> None:
    _workspace(tmp_path)
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {"name": "metagit_campaign_context", "arguments": {}},
        },
    )
    assert response is not None
    assert response["error"]["code"] == -32602

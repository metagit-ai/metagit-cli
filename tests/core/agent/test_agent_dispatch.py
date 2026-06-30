#!/usr/bin/env python
"""Tests for agent dispatch-plan service and CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from metagit.cli.main import cli
from metagit.core.agent.dispatch import AgentDispatchService
from metagit.core.agent.registry import AgentTemplateRegistry
from metagit.core.agent.service import AgentService
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.mcp.runtime import MetagitMcpRuntime


def _workspace_manifest() -> str:
    return "\n".join(
        [
            "name: workspace",
            "kind: application",
            "workspace:",
            "  projects:",
            "    - name: my-api",
            "      repos:",
            "        - name: backend",
            "          path: my-api/backend",
            "          sync: true",
            "      agent_instructions: Stay in project scope.",
            "  agent_instructions: Workspace overseer rules.",
        ]
    ) + "\n"


def test_dispatch_plan_repo_implementer_handoff(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_workspace_manifest(), encoding="utf-8")
    loaded = MetagitConfigManager(config_path=tmp_path / ".metagit.yml").load_config()
    assert not isinstance(loaded, Exception)
    registry = AgentTemplateRegistry(manifest_root=tmp_path)
    plan = AgentDispatchService(
        registry=registry,
        manifest_root=tmp_path,
        config=loaded,
    ).build_plan(
        "repo-implementer",
        vendor="cursor",
        project="my-api",
        repo="backend",
        task="implement auth middleware",
    )
    assert plan.template_id == "repo-implementer"
    assert plan.install.needed is True
    assert plan.handoff.prompt_kind == "subagent-handoff"
    assert plan.handoff.mcp_resources
    assert "metagit://repo/my-api/backend/card" in plan.handoff.mcp_resources
    assert "subagent-handoff" in plan.handoff.prompt
    assert "--project my-api" in plan.handoff.context_pack
    assert "--repo backend" in plan.handoff.context_pack
    assert "@repo-implementer" in plan.launch["cursor"]
    assert "auth middleware" in plan.launch["cursor"]
    assert plan.handoff.effective_instructions
    assert "manifest edits" in plan.out_of_scope[0]


def test_dispatch_plan_detects_installed_artifact(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_workspace_manifest(), encoding="utf-8")
    agent_path = tmp_path / ".cursor" / "agents"
    agent_path.mkdir(parents=True)
    (agent_path / "repo-implementer.md").write_text("# agent", encoding="utf-8")
    service = AgentService(manifest_root=tmp_path)
    plan = service.dispatch_plan(
        "repo-implementer",
        vendor="cursor",
        project="my-api",
        repo="backend",
    )
    assert plan.install.needed is False


def test_dispatch_plan_requires_repo_scope_inputs(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_workspace_manifest(), encoding="utf-8")
    service = AgentService(manifest_root=tmp_path)
    with pytest.raises(Exception, match="require --project and --repo"):
        service.dispatch_plan("repo-implementer", vendor="claude_code")


def test_dispatch_plan_cli_json(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_workspace_manifest(), encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "agent",
            "dispatch-plan",
            "repo-implementer",
            "--root",
            str(tmp_path),
            "--project",
            "my-api",
            "--repo",
            "backend",
            "--vendor",
            "cursor",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["template_id"] == "repo-implementer"
    assert "launch" in payload


def test_mcp_agent_dispatch_plan(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_workspace_manifest(), encoding="utf-8")
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 90,
            "method": "tools/call",
            "params": {
                "name": "metagit_agent_dispatch_plan",
                "arguments": {
                    "template_id": "repo-implementer",
                    "vendor": "cursor",
                    "project_name": "my-api",
                    "repo_name": "backend",
                },
            },
        }
    )
    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["template_id"] == "repo-implementer"
    assert payload["handoff"]["prompt_kind"] == "subagent-handoff"
    assert payload["handoff"]["mcp_resources"]
    assert payload["handoff"]["mcp_resources"][0] == "metagit://catalog"


def test_mcp_agent_catalog_lists_templates(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_workspace_manifest(), encoding="utf-8")
    runtime = MetagitMcpRuntime(root=str(tmp_path))
    response = runtime._handle_request(
        {
            "jsonrpc": "2.0",
            "id": 91,
            "method": "tools/call",
            "params": {"name": "metagit_agent_catalog", "arguments": {}},
        }
    )
    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert len(payload["templates"]) >= 10

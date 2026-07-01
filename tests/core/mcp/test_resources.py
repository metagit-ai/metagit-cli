#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.resources
"""

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.models import McpActivationState, WorkspaceStatus
from metagit.core.mcp.resources import ResourcePublisher
from metagit.core.mcp.services.ops_log import OperationsLogService


def test_workspace_resources_available_when_active() -> None:
    ops = OperationsLogService()
    ops.append(action="sync", detail="repo-a fetch")
    publisher = ResourcePublisher(ops_log=ops)
    config = MetagitConfig(
        name="metagit-test",
        kind="application",
        workspace={"projects": [{"name": "default", "repos": []}]},
    )
    status = WorkspaceStatus(state=McpActivationState.ACTIVE, root_path="/tmp/ws")

    config_resource = publisher.get_resource(
        uri="metagit://workspace/config",
        status=status,
        config=config,
        config_path="/tmp/ws/.metagit.yml",
        workspace_root="/tmp/ws",
    )
    repos_resource = publisher.get_resource(
        uri="metagit://workspace/repos/status",
        status=status,
        config=config,
        repos_status=[{"repo_name": "repo-a"}],
    )
    ops_resource = publisher.get_resource(
        uri="metagit://workspace/ops-log",
        status=status,
    )
    catalog_resource = publisher.get_resource(
        uri="metagit://catalog",
        status=status,
        config=config,
    )

    assert config_resource["uri"] == "metagit://workspace/config"
    assert config_resource["data"]["view"] == "summary"
    assert repos_resource["uri"] == "metagit://workspace/repos/status"
    assert len(ops_resource["data"]) == 1
    assert catalog_resource["data"]["schema_version"] == "1.0"

#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.tool_registry
"""

from metagit.core.mcp.models import McpActivationState, WorkspaceStatus
from metagit.core.mcp.tool_registry import ToolRegistry


def test_inactive_registry_exposes_only_safe_tools() -> None:
    registry = ToolRegistry()
    status = WorkspaceStatus(
        state=McpActivationState.INACTIVE_MISSING_CONFIG,
        root_path=None,
        reason="missing",
    )

    tools = registry.list_tools(status=status)

    assert tools == [
        "metagit_workspace_status",
        "metagit_bootstrap_config_plan_only",
    ]


def test_active_registry_exposes_full_toolset() -> None:
    registry = ToolRegistry()
    status = WorkspaceStatus(
        state=McpActivationState.ACTIVE,
        root_path="/tmp/workspace",
        reason=None,
    )

    tools = registry.list_tools(status=status)

    assert "metagit_workspace_status" in tools
    assert "metagit_workspace_index" in tools
    assert "metagit_workspace_search" in tools
    assert "metagit_workspace_grep_info" in tools
    assert "metagit_repo_search" in tools
    assert "metagit_upstream_hints" in tools
    assert "metagit_repo_sync" in tools
    assert "metagit_workspace_sync" in tools
    assert "metagit_project_context_switch" in tools
    assert "metagit_workspace_state_snapshot" in tools
    assert "metagit_workspace_state_restore" in tools
    assert "metagit_session_update" in tools
    assert "metagit_cross_project_dependencies" in tools
    assert "metagit_suggest_graph_relationships" in tools
    assert "metagit_apply_graph_relationships" in tools
    assert "metagit_gitnexus_group_sync" in tools
    assert "metagit_workspace_health_check" in tools
    assert "metagit_workspace_semantic_search" in tools
    assert "metagit_workspace_discover" in tools
    assert "metagit_project_template_apply" in tools
    assert "metagit_bootstrap_config_plan_only" not in tools

#!/usr/bin/env python
"""
Tool registry for Metagit MCP runtime.
"""

from metagit.core.mcp.models import McpActivationState, WorkspaceStatus


class ToolRegistry:
    """State-aware registry of available MCP tool names."""

    _inactive_tools: list[str] = [
        "metagit_workspace_status",
        "metagit_bootstrap_config_plan_only",
        "metagit_version_check",
        "metagit_version_upgrade",
    ]
    _active_tools: list[str] = [
        "metagit_workspace_status",
        "metagit_workspace_index",
        "metagit_workspace_search",
        "metagit_workspace_grep_info",
        "metagit_workspace_semantic_search",
        "metagit_repo_search",
        "metagit_upstream_hints",
        "metagit_repo_inspect",
        "metagit_repo_sync",
        "metagit_workspace_sync",
        "metagit_bootstrap_config",
        "metagit_project_context_switch",
        "metagit_workspace_state_snapshot",
        "metagit_workspace_state_restore",
        "metagit_session_update",
        "metagit_cross_project_dependencies",
        "metagit_export_workspace_graph_cypher",
        "metagit_suggest_graph_relationships",
        "metagit_apply_graph_relationships",
        "metagit_gitnexus_group_sync",
        "metagit_workspace_health_check",
        "metagit_context_pack",
        "metagit_objective_list",
        "metagit_objective_upsert",
        "metagit_approval_request",
        "metagit_approval_list",
        "metagit_approval_resolve",
        "metagit_repo_card",
        "metagit_workspace_discover",
        "metagit_workspace_list",
        "metagit_workspace_projects_list",
        "metagit_workspace_project_add",
        "metagit_workspace_project_remove",
        "metagit_workspace_repos_list",
        "metagit_workspace_repo_add",
        "metagit_workspace_repo_remove",
        "metagit_workspace_project_rename",
        "metagit_workspace_repo_rename",
        "metagit_workspace_repo_move",
        "metagit_project_template_apply",
        "metagit_agent_catalog",
        "metagit_agent_dispatch_plan",
        "metagit_version_check",
        "metagit_version_upgrade",
    ]

    def list_tools(self, status: WorkspaceStatus) -> list[str]:
        """List available tools for the provided workspace status."""
        if status.state == McpActivationState.ACTIVE:
            return self._active_tools.copy()
        return self._inactive_tools.copy()

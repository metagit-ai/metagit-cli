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
    ]
    _active_tools: list[str] = [
        "metagit_workspace_status",
        "metagit_workspace_index",
        "metagit_workspace_search",
        "metagit_repo_search",
        "metagit_upstream_hints",
        "metagit_repo_inspect",
        "metagit_repo_sync",
        "metagit_bootstrap_config",
    ]

    def list_tools(self, status: WorkspaceStatus) -> list[str]:
        """List available tools for the provided workspace status."""
        if status.state == McpActivationState.ACTIVE:
            return self._active_tools.copy()
        return self._inactive_tools.copy()

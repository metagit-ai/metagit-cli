#!/usr/bin/env python
"""
Workspace status MCP tool implementation.
"""

from metagit.core.mcp.models import WorkspaceStatus


def metagit_workspace_status(status: WorkspaceStatus) -> dict[str, str | None]:
    """Return structured workspace status details."""
    return {
        "state": status.state.value,
        "root_path": status.root_path,
        "reason": status.reason,
    }

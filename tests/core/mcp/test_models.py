#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.models
"""

from metagit.core.mcp.models import McpActivationState, WorkspaceStatus


def test_activation_state_values() -> None:
    assert McpActivationState.ACTIVE.value == "active"
    assert (
        McpActivationState.INACTIVE_MISSING_CONFIG.value
        == "inactive_missing_config"
    )
    assert (
        McpActivationState.INACTIVE_INVALID_CONFIG.value
        == "inactive_invalid_config"
    )


def test_workspace_status_model() -> None:
    status = WorkspaceStatus(
        state=McpActivationState.ACTIVE,
        root_path="/tmp/workspace",
        reason=None,
    )
    assert status.state == McpActivationState.ACTIVE
    assert status.root_path == "/tmp/workspace"
    assert status.reason is None

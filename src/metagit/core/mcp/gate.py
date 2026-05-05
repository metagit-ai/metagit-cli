#!/usr/bin/env python
"""
Workspace gate evaluation for Metagit MCP runtime.
"""

import os
from pathlib import Path
from typing import Optional

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.mcp.models import McpActivationState, WorkspaceStatus


class WorkspaceGate:
    """Evaluate whether workspace is active for MCP tool exposure."""

    _config_file_name: str = ".metagit.yml"

    def evaluate(self, root_path: Optional[str]) -> WorkspaceStatus:
        """Evaluate root state as active, missing config, or invalid config."""
        if not root_path:
            return WorkspaceStatus(
                state=McpActivationState.INACTIVE_MISSING_CONFIG,
                root_path=None,
                reason="Workspace root could not be resolved.",
            )

        config_path = os.path.join(root_path, self._config_file_name)
        if not os.path.exists(config_path):
            return WorkspaceStatus(
                state=McpActivationState.INACTIVE_MISSING_CONFIG,
                root_path=str(Path(root_path).resolve()),
                reason=f"Configuration file not found: {self._config_file_name}",
            )

        manager = MetagitConfigManager(config_path=Path(config_path))
        result = manager.load_config()
        if isinstance(result, Exception):
            return WorkspaceStatus(
                state=McpActivationState.INACTIVE_INVALID_CONFIG,
                root_path=str(Path(root_path).resolve()),
                reason=str(result),
            )

        return WorkspaceStatus(
            state=McpActivationState.ACTIVE,
            root_path=str(Path(root_path).resolve()),
            reason=None,
        )

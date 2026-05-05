#!/usr/bin/env python
"""
Protocol contracts for Metagit MCP components.
"""

from typing import Protocol

from metagit.core.mcp.models import WorkspaceStatus


class WorkspaceRootResolverProtocol(Protocol):
    """Resolve the effective workspace root for the MCP runtime."""

    def resolve(self, cwd: str, cli_root: str | None = None) -> str | None:
        """Resolve and return a workspace root path, if available."""


class WorkspaceGateProtocol(Protocol):
    """Evaluate whether MCP should expose active tooling."""

    def evaluate(self, root_path: str | None) -> WorkspaceStatus:
        """Return the current workspace status for tool gating."""

#!/usr/bin/env python
"""
Resource publishing for Metagit MCP runtime.
"""

from typing import Any

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.ops_log import OperationsLogService


class ResourcePublisher:
    """Serve MCP resources for workspace config and status views."""

    def __init__(self, ops_log: OperationsLogService) -> None:
        self._ops_log = ops_log

    def get_resource(
        self,
        uri: str,
        config: MetagitConfig | None = None,
        repos_status: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Return a resource payload for known URIs."""
        if uri == "metagit://workspace/config":
            return {"uri": uri, "data": config.model_dump(exclude_none=True) if config else {}}
        if uri == "metagit://workspace/repos/status":
            return {"uri": uri, "data": repos_status or []}
        if uri == "metagit://workspace/ops-log":
            return {"uri": uri, "data": self._ops_log.list_entries()}
        return {"uri": uri, "error": "Unknown resource URI"}

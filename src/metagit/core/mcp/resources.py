#!/usr/bin/env python
"""
Resource publishing for Metagit MCP runtime.
"""

from typing import Any, Optional

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.ops_log import OperationsLogService
from metagit.core.mcp.services.session_store import SessionStore


class ResourcePublisher:
    """Serve MCP resources for workspace config and status views."""

    def __init__(self, ops_log: OperationsLogService) -> None:
        self._ops_log = ops_log

    def get_resource(
        self,
        uri: str,
        config: MetagitConfig | None = None,
        repos_status: list[dict[str, Any]] | None = None,
        workspace_root: Optional[str] = None,
        health_payload: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Return a resource payload for known URIs."""
        if uri == "metagit://workspace/config":
            return {
                "uri": uri,
                "data": config.model_dump(exclude_none=True) if config else {},
            }
        if uri == "metagit://workspace/repos/status":
            return {"uri": uri, "data": repos_status or []}
        if uri == "metagit://workspace/ops-log":
            return {"uri": uri, "data": self._ops_log.list_entries()}
        if uri == "metagit://workspace/health":
            return {"uri": uri, "data": health_payload or {}}
        if uri == "metagit://workspace/context":
            if not workspace_root:
                return {"uri": uri, "data": {"active_project": None}}
            meta = SessionStore(workspace_root=workspace_root).get_workspace_meta()
            session = (
                SessionStore(workspace_root=workspace_root).get_project_session(
                    project_name=meta.active_project
                )
                if meta.active_project
                else None
            )
            return {
                "uri": uri,
                "data": {
                    "active_project": meta.active_project,
                    "last_switch_at": meta.last_switch_at,
                    "session": session.model_dump(mode="json") if session else None,
                },
            }
        return {"uri": uri, "error": "Unknown resource URI"}

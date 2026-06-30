#!/usr/bin/env python
"""
Resource publishing for Metagit MCP runtime.
"""

from typing import Any, Optional

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.models import WorkspaceStatus
from metagit.core.mcp.resource_service import ResourceContext, ResourceService, resource_json_text
from metagit.core.mcp.services.ops_log import OperationsLogService


class ResourcePublisher:
    """Serve MCP resources for workspace config and status views."""

    def __init__(self, ops_log: OperationsLogService) -> None:
        self._service = ResourceService(ops_log=ops_log)

    @property
    def service(self) -> ResourceService:
        """Underlying layered resource service."""
        return self._service

    def get_resource(
        self,
        uri: str,
        *,
        status: WorkspaceStatus,
        config: MetagitConfig | None = None,
        config_path: str = "",
        workspace_root: Optional[str] = None,
        session_root: Optional[str] = None,
        definition_root: Optional[str] = None,
        repos_status: list[dict[str, Any]] | None = None,
        health_payload: Optional[dict[str, Any]] = None,
        workspace_dedupe: Any = None,
    ) -> dict[str, Any]:
        """Return a legacy resource payload dict for known URIs."""
        resolved_workspace = workspace_root or status.root_path or ""
        resolved_session = session_root or status.root_path or resolved_workspace
        resolved_definition = definition_root or status.root_path or resolved_workspace
        context = ResourceContext(
            status=status,
            config=config,
            config_path=config_path or (f"{status.root_path}/.metagit.yml" if status.root_path else ""),
            workspace_root=resolved_workspace,
            session_root=resolved_session,
            definition_root=resolved_definition,
            repos_status=repos_status or [],
            health_payload=health_payload,
            workspace_dedupe=workspace_dedupe,
        )
        result = self._service.read(uri, context)
        if result.error:
            return {"uri": uri, "error": result.error}
        if result.mime_type == "text/plain":
            return {"uri": uri, "mime_type": result.mime_type, "text": result.text or ""}
        return {"uri": uri, "data": result.data}

    def read_resource(
        self,
        uri: str,
        *,
        context: ResourceContext,
    ) -> tuple[str, str]:
        """Return MCP mime type and serialized text for ``resources/read``."""
        result = self._service.read(uri, context)
        return result.mime_type, resource_json_text(result)

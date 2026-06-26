#!/usr/bin/env python
"""
MCP adapter for provider source sync.
"""

from __future__ import annotations

from typing import Any, Optional

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.project.source_models import SourceSpec, SourceSyncMode
from metagit.core.project.source_sync_runner import (
    SourceSyncRunRequest,
    run_source_sync,
)
from metagit.core.utils.logging import UnifiedLogger


def build_source_spec_from_arguments(arguments: dict[str, Any]) -> SourceSpec:
    """Build ``SourceSpec`` from MCP tool arguments."""
    provider = str(arguments.get("provider", "")).strip()
    include_patterns = arguments.get("include_patterns")
    ignore_patterns = arguments.get("ignore_patterns")
    return SourceSpec(
        provider=provider,
        org=_optional_str(arguments.get("org")),
        user=_optional_str(arguments.get("user")),
        group=_optional_str(arguments.get("group")),
        recursive=bool(arguments.get("recursive", True)),
        include_archived=bool(arguments.get("include_archived", False)),
        include_forks=bool(arguments.get("include_forks", False)),
        path_prefix=_optional_str(arguments.get("path_prefix")),
        include_patterns=_string_list(include_patterns),
        ignore_patterns=_string_list(ignore_patterns),
        name_strategy=str(arguments.get("name_strategy", "namespaced")),
        ensure=bool(arguments.get("ensure", False)),
        refresh_metadata=bool(arguments.get("refresh_metadata", False)),
        enrich_topics=bool(arguments.get("enrich_topics", True)),
    )


def run_mcp_source_sync(
    *,
    app_config: AppConfig,
    logger: UnifiedLogger,
    config: MetagitConfig,
    config_path: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Execute source sync from MCP tool arguments."""
    if bool(arguments.get("from_manifest", False)):
        project_name = str(arguments.get("project_name", "")).strip()
        if not project_name:
            return {
                "ok": False,
                "errors": [{"kind": "invalid_arguments", "message": "project_name is required"}],
            }
        from metagit.core.project.source_manifest_sync import SourceManifestSyncService
        from metagit.core.workspace.root_resolver import resolve_session_root

        result = SourceManifestSyncService().sync_project(
            app_config=app_config,
            logger=logger,
            config=config,
            config_path=config_path,
            project_name=project_name,
            source_id=_optional_str(arguments.get("source_id")),
            apply=bool(arguments.get("apply", False)),
            force=bool(arguments.get("force", False)),
            sync_clones=bool(arguments.get("sync", False)) and bool(arguments.get("apply", False)),
            session_root=resolve_session_root(config_path),
            requested_by=str(arguments.get("requested_by", "mcp")),
        )
        return result.model_dump(mode="json")

    project_name = str(arguments.get("project_name", "")).strip()
    if not project_name:
        return {
            "ok": False,
            "errors": [{"kind": "invalid_arguments", "message": "project_name is required"}],
        }

    try:
        spec = build_source_spec_from_arguments(arguments)
    except Exception as exc:
        return {
            "ok": False,
            "errors": [{"kind": "invalid_arguments", "message": str(exc)}],
        }

    mode_value = str(arguments.get("mode", SourceSyncMode.DISCOVER.value))
    apply = bool(arguments.get("apply", False))
    confirm = bool(arguments.get("confirm", False))
    sync_clones = bool(arguments.get("sync", False))

    result = run_source_sync(
        app_config=app_config,
        logger=logger,
        config=config,
        config_path=config_path,
        request=SourceSyncRunRequest(
            spec=spec,
            mode=SourceSyncMode(mode_value),
            project_name=project_name,
            apply=apply,
            confirm_reconcile=confirm,
            sync_clones=sync_clones and apply,
        ),
    )
    return result.model_dump(mode="json")


def _optional_str(value: object) -> Optional[str]:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]

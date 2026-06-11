#!/usr/bin/env python
"""
Shared orchestration for provider source sync (CLI and MCP).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.project.manager import project_manager_from_app
from metagit.core.project.source_models import (
    SourceSpec,
    SourceSyncError,
    SourceSyncMode,
    SourceSyncResult,
)
from metagit.core.project.source_sync import SourceSyncService
from metagit.core.utils.logging import UnifiedLogger
from metagit.core.workspace.models import WorkspaceProject


@dataclass(frozen=True)
class SourceSyncRunRequest:
    """Inputs for a single source sync run."""

    spec: SourceSpec
    mode: SourceSyncMode
    project_name: str
    apply: bool = False
    confirm_reconcile: bool = False
    sync_clones: bool = False


def resolve_workspace_project(
    config: MetagitConfig,
    project_name: str,
) -> Optional[WorkspaceProject]:
    """Return the workspace project entry for ``project_name``."""
    if not config.workspace:
        return None
    return next(
        (item for item in config.workspace.projects if item.name == project_name),
        None,
    )


def run_source_sync(
    *,
    app_config: AppConfig,
    logger: UnifiedLogger,
    config: MetagitConfig,
    config_path: str,
    request: SourceSyncRunRequest,
) -> SourceSyncResult:
    """Discover, plan, optionally apply manifest changes, optionally clone repos."""
    workspace_project = resolve_workspace_project(config, request.project_name)
    if workspace_project is None:
        return SourceSyncResult(
            ok=False,
            spec=request.spec.model_dump(mode="json"),
            errors=[
                SourceSyncError(
                    kind="project_not_found",
                    message=(
                        f"Project '{request.project_name}' not found in workspace "
                        "configuration"
                    ),
                )
            ],
        )

    service = SourceSyncService(app_config, logger)
    discovered_result = service.discover(request.spec)
    if isinstance(discovered_result, Exception):
        return SourceSyncResult(
            ok=False,
            spec=request.spec.model_dump(mode="json"),
            errors=[
                SourceSyncError(
                    kind="discovery_failed",
                    message=str(discovered_result),
                )
            ],
        )

    plan = service.plan(
        request.spec,
        workspace_project,
        discovered_result,
        request.mode,
    )
    result = SourceSyncResult(
        ok=True,
        applied=False,
        spec=request.spec.model_dump(mode="json"),
        plan=plan,
    )

    if not request.apply or request.mode == SourceSyncMode.DISCOVER:
        return result

    if (
        request.mode == SourceSyncMode.RECONCILE
        and len(plan.to_remove) > 0
        and not request.confirm_reconcile
    ):
        result.ok = False
        result.errors.append(
            SourceSyncError(
                kind="reconcile_confirmation_required",
                message="Reconcile mode has removals. Re-run with confirm enabled.",
            )
        )
        return result

    updated_project = service.apply_plan(workspace_project, plan, request.mode)
    for index, item in enumerate(config.workspace.projects):
        if item.name == updated_project.name:
            config.workspace.projects[index] = updated_project
            break

    config_manager = MetagitConfigManager(config_path=config_path)
    save_result = config_manager.save_config(config, config_path)
    if isinstance(save_result, Exception):
        result.ok = False
        result.errors.append(
            SourceSyncError(kind="save_failed", message=str(save_result))
        )
        return result

    result.applied = True

    if request.sync_clones:
        project_manager = project_manager_from_app(
            app_config,
            logger,
            metagit_config=config,
            project_name=request.project_name,
        )
        sync_ok = project_manager.sync(updated_project)
        if not sync_ok:
            result.ok = False
            result.errors.append(
                SourceSyncError(
                    kind="clone_sync_failed",
                    message=f"Failed to sync clones for project '{request.project_name}'",
                )
            )

    return result

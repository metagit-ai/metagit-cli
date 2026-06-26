#!/usr/bin/env python
"""
Manifest-driven multi-source sync for workspace.projects[].sources[].
"""

from __future__ import annotations

from typing import List, Optional

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.context.approval_service import ApprovalService
from metagit.core.project.source_models import (
    ProjectSource,
    SourceSyncError,
    SourceSyncMode,
    SourceSyncPlan,
    SourceSyncResult,
)
from metagit.core.project.source_sync import SourceSyncService
from metagit.core.utils.logging import UnifiedLogger
from metagit.core.workspace.models import WorkspaceProject


class SourceManifestSyncService:
    """Sync workspace project repos from declarative ``sources[]`` entries."""

    def sync_project(
        self,
        *,
        app_config: AppConfig,
        logger: UnifiedLogger,
        config: MetagitConfig,
        config_path: str,
        project_name: str,
        source_id: Optional[str] = None,
        apply: bool = False,
        force: bool = False,
        sync_clones: bool = False,
        session_root: Optional[str] = None,
        requested_by: str = "cli",
    ) -> SourceSyncResult:
        """Discover and optionally apply all enabled manifest sources."""
        project = _find_project(config, project_name)
        if project is None:
            return SourceSyncResult(
                ok=False,
                errors=[
                    SourceSyncError(
                        kind="project_not_found",
                        message=f"project '{project_name}' not found",
                    )
                ],
            )

        selected = _select_sources(project, source_id)
        if isinstance(selected, SourceSyncError):
            return SourceSyncResult(ok=False, errors=[selected])

        if not selected:
            return SourceSyncResult(
                ok=True,
                plan=SourceSyncPlan(discovered_count=0, filtered_count=0),
            )

        service = SourceSyncService(app_config, logger)
        combined = SourceSyncPlan()
        specs: list[dict] = []

        for source in selected:
            spec = source.to_source_spec()
            specs.append(spec.model_dump(mode="json"))
            discovered = service.discover(spec)
            if isinstance(discovered, Exception):
                return SourceSyncResult(
                    ok=False,
                    spec={"sources": specs},
                    errors=[
                        SourceSyncError(
                            kind="discovery_failed",
                            message=f"{source.id}: {discovered}",
                        )
                    ],
                )
            plan = service.plan(spec, project, discovered, source.mode)
            _merge_plan(combined, plan)
            project = _preview_adds_and_updates(service, project, plan)

        result = SourceSyncResult(
            ok=True,
            applied=False,
            spec={"sources": specs},
            plan=combined,
        )

        if not apply:
            return result

        updated = _apply_partial_plan(service, project, combined)
        for index, item in enumerate(config.workspace.projects):
            if item.name == updated.name:
                config.workspace.projects[index] = updated
                break

        if combined.to_remove and not force:
            if session_root is None:
                result.ok = False
                result.errors.append(
                    SourceSyncError(
                        kind="session_root_required",
                        message="session root required to queue reconcile removals",
                    )
                )
                return result
            for source in selected:
                if source.mode != SourceSyncMode.RECONCILE:
                    continue
                source_removals = [repo for repo in combined.to_remove if repo.source_id == source.id]
                if not source_removals:
                    continue
                approval = ApprovalService(workspace_root=session_root).request(
                    action="source_sync_reconcile",
                    payload={
                        "project": project_name,
                        "source_id": source.id,
                        "to_remove": [repo.model_dump(mode="json") for repo in source_removals],
                    },
                    requested_by=requested_by,
                )
                result.pending_approval_id = approval.id
        elif combined.to_remove and force:
            updated = service.apply_plan(updated, combined, SourceSyncMode.RECONCILE)
            for index, item in enumerate(config.workspace.projects):
                if item.name == updated.name:
                    config.workspace.projects[index] = updated
                    break

        save_result = MetagitConfigManager(config_path=config_path).save_config(config, config_path)
        if isinstance(save_result, Exception):
            result.ok = False
            result.errors.append(SourceSyncError(kind="save_failed", message=str(save_result)))
            return result

        result.applied = True

        if sync_clones and result.ok:
            from metagit.core.project.manager import project_manager_from_app
            from metagit.core.project.source_sync_runner import (
                resolve_workspace_project,
            )

            refreshed = resolve_workspace_project(config, project_name)
            if refreshed is not None:
                manager = project_manager_from_app(
                    app_config,
                    logger,
                    metagit_config=config,
                    project_name=project_name,
                )
                if not manager.sync(refreshed):
                    result.ok = False
                    result.errors.append(
                        SourceSyncError(
                            kind="clone_sync_failed",
                            message=f"Failed to sync clones for '{project_name}'",
                        )
                    )

        return result


def upsert_project_source(
    project: WorkspaceProject,
    source: ProjectSource,
) -> WorkspaceProject:
    """Insert or replace a ``sources[]`` entry by id."""
    sources = [item for item in project.sources if item.id != source.id]
    sources.append(source)
    return project.model_copy(update={"sources": sources})


def _find_project(
    config: MetagitConfig,
    project_name: str,
) -> Optional[WorkspaceProject]:
    if not config.workspace:
        return None
    return next(
        (item for item in config.workspace.projects if item.name == project_name),
        None,
    )


def _select_sources(
    project: WorkspaceProject,
    source_id: Optional[str],
) -> List[ProjectSource] | SourceSyncError:
    enabled = [source for source in project.sources if source.enabled]
    if source_id is None:
        return enabled
    matches = [source for source in enabled if source.id == source_id]
    if not matches:
        return SourceSyncError(
            kind="source_not_found",
            message=f"source '{source_id}' not found on project '{project.name}'",
        )
    return matches


def _merge_plan(target: SourceSyncPlan, incoming: SourceSyncPlan) -> None:
    target.discovered_count += incoming.discovered_count
    target.filtered_count += incoming.filtered_count
    target.unchanged += incoming.unchanged
    target.to_add.extend(incoming.to_add)
    target.to_update.extend(incoming.to_update)
    target.to_remove.extend(incoming.to_remove)


def _preview_adds_and_updates(
    service: SourceSyncService,
    project: WorkspaceProject,
    plan: SourceSyncPlan,
) -> WorkspaceProject:
    """Apply in-memory add/update preview so later sources see new repos."""
    partial = SourceSyncPlan(
        to_add=list(plan.to_add),
        to_update=list(plan.to_update),
    )
    if not partial.to_add and not partial.to_update:
        return project
    return service.apply_plan(project, partial, SourceSyncMode.ADDITIVE)


def _apply_partial_plan(
    service: SourceSyncService,
    project: WorkspaceProject,
    plan: SourceSyncPlan,
) -> WorkspaceProject:
    partial = SourceSyncPlan(
        to_add=list(plan.to_add),
        to_update=list(plan.to_update),
    )
    updated = service.apply_plan(project, partial, SourceSyncMode.ADDITIVE)
    return updated

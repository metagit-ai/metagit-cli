#!/usr/bin/env python
"""
Build tier-0 workspace map payloads from workspace catalog snapshots.
"""

from __future__ import annotations

from typing import Any, Optional

from metagit.core.config.models import MetagitConfig
from metagit.core.context.models import (
    WorkspaceMapEntry,
    WorkspaceMapProject,
    WorkspaceMapResult,
)
from metagit.core.workspace.catalog_models import WorkspaceSummary
from metagit.core.workspace.catalog_service import WorkspaceCatalogService


def _normalized_tag_list(tags: Any) -> Optional[list[str]]:
    """Convert workspace index tag dict rows into stable string lists."""
    if not isinstance(tags, dict) or not tags:
        return None
    return [f"{key}={value}" for key, value in sorted(tags.items())]


class WorkspaceMapService:
    """Produce ``WorkspaceMapResult`` from workspace catalog listings."""

    def __init__(
        self,
        catalog_service: Optional[WorkspaceCatalogService] = None,
    ) -> None:
        self._catalog = catalog_service or WorkspaceCatalogService()

    def build(
        self,
        config: MetagitConfig,
        config_path: str,
        workspace_root: str,
        *,
        active_project: Optional[str] = None,
    ) -> WorkspaceMapResult:
        """Assemble tier-0 map fields from catalog summary, projects, and index."""
        listing = self._catalog.list_workspace(
            config=config,
            config_path=config_path,
            workspace_root=workspace_root,
            include_index=True,
        )
        if not listing.ok or listing.data is None:
            return WorkspaceMapResult(
                workspace_name=config.name,
                workspace_root=workspace_root,
                config_path=config_path,
                project_count=0,
                repo_count=0,
                projects=[],
                repos=[],
                active_project=active_project,
            )

        payload = listing.data
        summary = WorkspaceSummary.model_validate(payload["summary"])

        raw_projects = payload.get("projects") or []
        projects = [
            WorkspaceMapProject(
                name=proj["name"],
                repo_count=proj["repo_count"],
                description=proj.get("description"),
                tags=[
                    f"{key}={value}"
                    for key, value in sorted((proj.get("tags") or {}).items())
                ],
                protected=bool(proj.get("protected")),
            )
            for proj in raw_projects
        ]

        repos: list[WorkspaceMapEntry] = []
        for row in payload.get("repos_index") or []:
            tags = _normalized_tag_list(row.get("tags"))
            repos.append(
                WorkspaceMapEntry(
                    project_name=row["project_name"],
                    repo_name=row["repo_name"],
                    repo_path=str(row["repo_path"]),
                    status=str(row["status"]),
                    exists=bool(row["exists"]),
                    tags=tags,
                )
            )

        return WorkspaceMapResult(
            workspace_name=config.name,
            workspace_root=summary.workspace_root,
            config_path=summary.definition_path,
            project_count=summary.project_count,
            repo_count=summary.repo_count,
            projects=projects,
            repos=repos,
            active_project=active_project,
        )

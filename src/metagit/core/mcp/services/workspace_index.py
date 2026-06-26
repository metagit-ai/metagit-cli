#!/usr/bin/env python
"""
Workspace repository indexing service.
"""

from pathlib import Path
from typing import Any

from metagit.core.config.models import MetagitConfig
from metagit.core.utils.common import is_git_repository
from metagit.core.workspace import workspace_dedupe
from metagit.core.workspace.protection import merge_project_repo_tags

_MANIFEST_ROOT_PATHS = frozenset({".", "./"})


class WorkspaceIndexService:
    """Build normalized repository status rows from workspace configuration."""

    def build_index(
        self,
        config: MetagitConfig,
        workspace_root: str,
        *,
        definition_root: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return repository index rows for all configured workspace repos."""
        rows: list[dict[str, Any]] = []
        if not config.workspace:
            return rows

        for project in config.workspace.projects:
            for repo in project.repos:
                resolved_path = self._resolve_repo_path(
                    workspace_root=workspace_root,
                    definition_root=definition_root or workspace_root,
                    project_name=project.name,
                    configured_path=repo.path,
                    repo_name=repo.name,
                )
                mount = Path(resolved_path)
                exists = mount.is_dir() or (mount.is_symlink() and mount.resolve().is_dir())
                is_git_repo = bool(is_git_repository(resolved_path)) if exists else False
                status = "synced" if exists and is_git_repo else "configured_missing"
                project_tags = dict(project.tags)
                repo_tags = dict(repo.tags)
                effective_tags = merge_project_repo_tags(project, repo)
                rows.append(
                    {
                        "project_name": project.name,
                        "repo_name": repo.name,
                        "configured_path": repo.path,
                        "repo_path": resolved_path,
                        "exists": exists,
                        "is_git_repo": is_git_repo,
                        "status": status,
                        "url": str(repo.url) if repo.url else None,
                        "sync": repo.sync if repo.sync is not None else False,
                        "project_tags": project_tags,
                        "repo_tags": repo_tags,
                        "tags": effective_tags,
                        "project_protected": bool(project.protected),
                    }
                )
        return rows

    def _resolve_repo_path(
        self,
        workspace_root: str,
        definition_root: str,
        project_name: str,
        configured_path: str | None,
        repo_name: str,
    ) -> str:
        """Resolve repository mount path (matches project sync layout)."""
        if configured_path:
            path = Path(configured_path).expanduser()
            normalized = str(path).replace("\\", "/").rstrip("/") or "."
            if normalized in _MANIFEST_ROOT_PATHS:
                return str(Path(definition_root).resolve())
            if path.is_absolute():
                return str(path.resolve())
            return str((Path(workspace_root) / path).resolve())
        return str(
            workspace_dedupe.project_mount_path(
                Path(workspace_root),
                project_name,
                repo_name,
            )
        )

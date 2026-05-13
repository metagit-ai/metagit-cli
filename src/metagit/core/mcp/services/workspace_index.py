#!/usr/bin/env python
"""
Workspace repository indexing service.
"""

import os
from pathlib import Path
from typing import Any

from metagit.core.config.models import MetagitConfig
from metagit.core.utils.common import is_git_repository


class WorkspaceIndexService:
    """Build normalized repository status rows from workspace configuration."""

    def build_index(
        self, config: MetagitConfig, workspace_root: str
    ) -> list[dict[str, Any]]:
        """Return repository index rows for all configured workspace repos."""
        rows: list[dict[str, Any]] = []
        if not config.workspace:
            return rows

        for project in config.workspace.projects:
            for repo in project.repos:
                resolved_path = self._resolve_repo_path(
                    workspace_root=workspace_root,
                    configured_path=repo.path,
                    repo_name=repo.name,
                )
                exists = os.path.isdir(resolved_path)
                is_git_repo = (
                    bool(is_git_repository(resolved_path)) if exists else False
                )
                status = "synced" if exists and is_git_repo else "configured_missing"
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
                        "tags": dict(repo.tags),
                    }
                )
        return rows

    def _resolve_repo_path(
        self,
        workspace_root: str,
        configured_path: str | None,
        repo_name: str,
    ) -> str:
        """Resolve repository path relative to workspace root when needed."""
        if configured_path:
            path = Path(configured_path).expanduser()
            if path.is_absolute():
                return str(path.resolve())
            return str((Path(workspace_root) / path).resolve())
        return str((Path(workspace_root) / repo_name).resolve())

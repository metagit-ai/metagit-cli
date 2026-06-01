#!/usr/bin/env python
"""Workspace project and repository protection helpers."""

from __future__ import annotations

from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import WorkspaceProject


def project_is_protected(project: WorkspaceProject) -> bool:
    """Return True when the workspace project group is protected."""
    return bool(project.protected)


def repo_is_protected(project: WorkspaceProject, repo: ProjectPath) -> bool:
    """Return True when the project or repo entry is protected."""
    return project_is_protected(project) or bool(repo.protected)


def merge_project_repo_tags(
    project: WorkspaceProject,
    repo: ProjectPath,
) -> dict[str, str]:
    """Merge project tags with repo tags; repo values win on collision."""
    merged = dict(project.tags)
    merged.update(repo.tags)
    return merged

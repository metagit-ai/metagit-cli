#!/usr/bin/env python
"""
Resolve sync-root paths for workspace layout operations.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from metagit.core.appconfig.models import WorkspaceDedupeConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace import workspace_dedupe
from metagit.core.workspace.models import WorkspaceProject

_NAME_PATTERN = re.compile(r"^[\w][\w.-]*$")


def validate_layout_name(
    name: str,
    *,
    label: str = "name",
    reserved: frozenset[str] | set[str] | None = None,
) -> Optional[str]:
    """Return an error message when name is invalid for paths and sessions."""
    trimmed = name.strip()
    if not trimmed:
        return f"{label} is required"
    if trimmed in {".", ".."} or "/" in trimmed or "\\" in trimmed:
        return f"invalid {label}: {name!r}"
    if not _NAME_PATTERN.match(trimmed):
        return f"invalid {label} (use letters, digits, _, ., -): {name!r}"
    if reserved and (trimmed in reserved or trimmed.lstrip("._") in reserved):
        return f"invalid {label}: {name!r} is reserved (conflicts with campaigns/worktrees path)"
    return None


def sync_root_path(workspace_path: str) -> Path:
    """Resolved workspace sync root."""
    return Path(workspace_path).expanduser().resolve()


def project_dir(workspace_path: Path, project_name: str) -> Path:
    """Project folder under the sync root."""
    return workspace_path / project_name


def repo_mount_path(
    workspace_path: Path,
    project_name: str,
    repo_name: str,
) -> Path:
    """Repo mount path under a project folder."""
    return workspace_dedupe.project_mount_path(
        workspace_path,
        project_name,
        repo_name,
    )


def list_project_names(config: MetagitConfig) -> list[str]:
    """Return workspace project names from the manifest."""
    if not config.workspace:
        return []
    return [project.name for project in config.workspace.projects]


def project_exists_in_manifest(config: MetagitConfig, project_name: str) -> bool:
    """Return True when project_name is defined under workspace.projects."""
    return find_project(config, project_name) is not None


def resolve_active_project_name(
    config: MetagitConfig,
    *,
    explicit: Optional[str] = None,
    default_project: Optional[str] = None,
) -> Optional[str]:
    """
    Resolve the workspace project name for CLI context.

    Prefers an explicit ``-p`` value, then the app-config preference when it
    exists in the manifest, then the sole manifest project, then ``local`` when
    no workspace projects are defined. Returns ``None`` when multiple manifest
    projects exist and no unambiguous preference applies.
    """
    if explicit and explicit.strip():
        return explicit.strip()
    names = list_project_names(config)
    preferred = default_project.strip() if default_project and default_project.strip() else None
    if preferred and preferred in names:
        return preferred
    if len(names) == 1:
        return names[0]
    if not names:
        return "local"
    return None


def active_project_resolution_error(config: MetagitConfig) -> str:
    """Human-readable message when project context cannot be resolved."""
    names = list_project_names(config)
    if not names:
        return "No workspace projects defined in .metagit.yml; add one with `metagit project add`."
    return f"Multiple workspace projects ({', '.join(names)}); pass -p/--project."


def require_active_project_name(
    config: MetagitConfig,
    *,
    explicit: Optional[str] = None,
    default_project: Optional[str] = None,
) -> str:
    """Resolve active project or raise ValueError with guidance."""
    name = resolve_active_project_name(
        config,
        explicit=explicit,
        default_project=default_project,
    )
    if name:
        return name
    raise ValueError(active_project_resolution_error(config))


def find_project(
    config: MetagitConfig,
    project_name: str,
) -> Optional[WorkspaceProject]:
    """Locate a workspace project by name."""
    if not config.workspace:
        return None
    for project in config.workspace.projects:
        if project.name == project_name:
            return project
    return None


def find_repo(
    project: WorkspaceProject,
    repo_name: str,
) -> Optional[ProjectPath]:
    """Locate a repo entry on a project."""
    for repo in project.repos:
        if repo.name == repo_name:
            return repo
    return None


def dedupe_enabled(dedupe: Optional[WorkspaceDedupeConfig]) -> bool:
    """True when workspace dedupe layout applies."""
    return bool(dedupe and dedupe.enabled)


def canonical_for_repo(
    workspace_path: Path,
    dedupe: WorkspaceDedupeConfig,
    repo: ProjectPath,
) -> Optional[Path]:
    """Canonical checkout path when dedupe applies."""
    identity = workspace_dedupe.build_repo_identity(repo)
    if identity is None:
        return None
    return workspace_dedupe.canonical_path(
        workspace_path,
        dedupe,
        identity.repo_key,
    )

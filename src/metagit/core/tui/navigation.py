#!/usr/bin/env python
"""In-TUI project and repository navigation helpers (no nested FuzzyFinder)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from metagit.core.appconfig import load_config
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.project.manager import project_manager_from_app
from metagit.core.utils.common import open_editor
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger
from metagit.core.workspace.layout_resolver import find_project, list_project_names
from metagit.core.workspace.root_resolver import resolve_definition_root


@dataclass(frozen=True)
class ProjectRepoSelection:
    """Resolved selection from the in-TUI project → repo flow."""

    project: str
    repo: str
    path: str


def list_manifest_projects(manifest_path: str) -> list[str] | Exception:
    """Return workspace project names from a manifest path."""
    manager = MetagitConfigManager(manifest_path)
    config = manager.load_config()
    if isinstance(config, Exception):
        return config
    return list_project_names(config)


def list_manifest_repos(manifest_path: str, project_name: str) -> list[str] | Exception:
    """Return repository names for a workspace project."""
    manager = MetagitConfigManager(manifest_path)
    config = manager.load_config()
    if isinstance(config, Exception):
        return config
    project = find_project(config, project_name)
    if project is None:
        return ValueError(f"project not found: {project_name}")
    return [repo.name for repo in project.repos]


def open_selected_repo(
    *,
    app_config_path: str,
    manifest_path: str,
    project_name: str,
    repo_name: str,
) -> ProjectRepoSelection | Exception:
    """Resolve a project/repo mount path and open it in the configured editor."""
    app_config = load_config(app_config_path)
    if isinstance(app_config, Exception):
        return app_config

    manager = MetagitConfigManager(manifest_path)
    local_config = manager.load_config()
    if isinstance(local_config, Exception):
        return local_config

    logger = UnifiedLogger(LoggerConfig(minimal_console=True))
    project_manager = project_manager_from_app(
        app_config,
        logger,
        metagit_config=local_config,
        project_name=project_name,
    )
    definition_root = resolve_definition_root(manifest_path)
    selected = project_manager.resolve_selected_repo_path(
        local_config,
        project_name,
        repo_name,
        definition_root=definition_root,
    )
    if isinstance(selected, Exception):
        return selected
    if selected is None:
        return ValueError(f"repository not found: {project_name}/{repo_name}")

    path = str(Path(selected).resolve())
    editor_result = open_editor(app_config.editor, path)
    if isinstance(editor_result, Exception):
        return editor_result
    return ProjectRepoSelection(project=project_name, repo=repo_name, path=path)


def maybe_single_project(projects: list[str]) -> Optional[str]:
    """Return the only project name when the list has exactly one entry."""
    return projects[0] if len(projects) == 1 else None

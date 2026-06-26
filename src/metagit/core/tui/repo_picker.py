#!/usr/bin/env python
"""In-process repository picker for the Metagit TUI hub."""

from __future__ import annotations

from typing import Optional

import click

from metagit.core.appconfig import load_config
from metagit.core.appconfig.models import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.project.manager import project_manager_from_app
from metagit.core.utils.common import open_editor
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger
from metagit.core.workspace.layout_resolver import (
    active_project_resolution_error,
    resolve_active_project_name,
)
from metagit.core.workspace.root_resolver import resolve_definition_root


def run_repo_picker_session(
    *,
    app_config_path: str,
    manifest_path: Optional[str],
    repo_name: Optional[str] = None,
) -> Optional[str]:
    """
    Run the repo fuzzy finder and open the configured editor.

    Intended to run while the Metagit TUI hub has suspended terminal control
    so nested Textual apps can interact with stdin/stdout.

    Returns the selected repo path, or None when nothing was selected.
    """
    if not manifest_path:
        click.echo(
            "No .metagit.yml found. Run from a workspace root or pass --manifest to metagit tui.",
            err=True,
        )
        return None

    app_config = load_config(app_config_path)
    if isinstance(app_config, Exception):
        click.echo(f"Failed to load app config: {app_config}", err=True)
        return None

    manager = MetagitConfigManager(manifest_path)
    local_config = manager.load_config()
    if isinstance(local_config, Exception):
        click.echo(f"Failed to load manifest: {local_config}", err=True)
        return None

    project = resolve_active_project_name(
        local_config,
        explicit=None,
        default_project=app_config.workspace.default_project,
    )
    if not project:
        click.echo(active_project_resolution_error(local_config), err=True)
        return None

    return _select_and_open_repo(
        app_config=app_config,
        local_config=local_config,
        manifest_path=manifest_path,
        project=project,
        repo_name=repo_name,
    )


def _select_and_open_repo(
    *,
    app_config: AppConfig,
    local_config: MetagitConfig,
    manifest_path: str,
    project: str,
    repo_name: Optional[str],
) -> Optional[str]:
    logger = UnifiedLogger(LoggerConfig(minimal_console=False))
    project_manager = project_manager_from_app(
        app_config,
        logger,
        metagit_config=local_config,
        project_name=project,
    )
    definition_root = resolve_definition_root(manifest_path)

    if repo_name:
        selected_repo = project_manager.resolve_selected_repo_path(
            local_config,
            project,
            repo_name,
            definition_root=definition_root,
        )
    else:
        selected_repo = project_manager.select_repo(
            local_config,
            project,
            show_preview=app_config.workspace.ui_show_preview,
            menu_length=app_config.workspace.ui_menu_length,
            ignore_hidden=app_config.workspace.ui_ignore_hidden,
            agent_mode=False,
        )

    if isinstance(selected_repo, Exception):
        click.echo(f"Failed to select project repo: {selected_repo}", err=True)
        return None
    if selected_repo is None:
        click.echo("No repo selected.")
        return None

    click.echo(f"Selected repo: {selected_repo}")
    editor_result = open_editor(app_config.editor, selected_repo)
    if isinstance(editor_result, Exception):
        click.echo(f"Failed to open editor: {editor_result}", err=True)
    else:
        click.echo(f"Opened {selected_repo} in {app_config.editor}")
    return selected_repo

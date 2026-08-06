#!/usr/bin/env python
"""Top-level interactive project → repo navigation (FuzzyFinder)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from metagit.cli.shell_completion import complete_projects, complete_repos
from metagit.core.appconfig import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.project.manager import ProjectManager, resolve_effective_dedupe
from metagit.core.project.project_picker import select_project_name
from metagit.core.utils.common import open_editor
from metagit.core.workspace.layout_resolver import find_project, list_project_names
from metagit.core.workspace.root_resolver import resolve_definition_root, resolve_workspace_root

DEFAULT_MANIFEST = ".metagit.yml"


@click.command("nav")
@click.option(
    "--config",
    "-c",
    "manifest_path",
    default=".metagit.yml",
    show_default=True,
    help="Path to the metagit definition file",
)
@click.option(
    "--project",
    "-p",
    "project_name",
    default=None,
    help="Project within workspace (skips project picker)",
    shell_complete=complete_projects,
)
@click.option(
    "--repo",
    "repo_name",
    default=None,
    help="Repository name (skips repo picker)",
    shell_complete=complete_repos,
)
@click.pass_context
def nav_cmd(
    ctx: click.Context,
    manifest_path: str,
    project_name: Optional[str],
    repo_name: Optional[str],
) -> None:
    """Pick a project, then a repo, and open it in the configured editor."""
    logger = ctx.obj["logger"]
    if ctx.obj.get("agent_mode"):
        raise click.UsageError("Interactive navigation is disabled in agent mode")

    app_config: AppConfig = ctx.obj["config"]
    definition_from_ctx = ctx.obj.get("definition_path")
    effective_manifest = manifest_path
    if manifest_path == DEFAULT_MANIFEST and definition_from_ctx:
        effective_manifest = definition_from_ctx
    effective_manifest = str(Path(effective_manifest).expanduser())

    manager = MetagitConfigManager(effective_manifest)
    local_config = manager.load_config()
    if isinstance(local_config, Exception):
        raise click.ClickException(str(local_config))

    names = list_project_names(local_config)
    resolved_project = project_name
    if resolved_project:
        if find_project(local_config, resolved_project) is None and resolved_project != "local":
            raise click.ClickException(f"Project '{resolved_project}' not found in workspace configuration.")
    elif len(names) == 1:
        resolved_project = names[0]
    else:
        picked = select_project_name(
            names,
            menu_length=app_config.workspace.ui_menu_length,
        )
        if isinstance(picked, Exception):
            raise click.ClickException(str(picked))
        if picked is None:
            raise click.ClickException("No project selected")
        resolved_project = picked

    project = find_project(local_config, resolved_project) if resolved_project else None
    dedupe = resolve_effective_dedupe(app_config.workspace.dedupe, project)
    sync_root = resolve_workspace_root(effective_manifest, app_config.workspace.path)
    project_manager = ProjectManager(sync_root, logger, dedupe=dedupe)
    definition_root = resolve_definition_root(effective_manifest)

    if repo_name:
        selected_repo = project_manager.resolve_selected_repo_path(
            local_config,
            resolved_project,
            repo_name,
            definition_root=definition_root,
        )
    else:
        selected_repo = project_manager.select_repo(
            local_config,
            resolved_project,
            show_preview=app_config.workspace.ui_show_preview,
            menu_length=app_config.workspace.ui_menu_length,
            ignore_hidden=app_config.workspace.ui_ignore_hidden,
            agent_mode=False,
        )

    if isinstance(selected_repo, Exception):
        raise click.ClickException(str(selected_repo))
    if selected_repo is None:
        raise click.ClickException("No repo selected")

    logger.info(f"Selected repo: {selected_repo}")
    editor_result = open_editor(app_config.editor, selected_repo)
    if isinstance(editor_result, Exception):
        raise click.ClickException(f"Failed to open editor: {editor_result}")
    logger.info(f"Opened {selected_repo} in {app_config.editor}")

"""
Workspace subcommand
"""

import os
import sys
from pathlib import Path
from typing import List

import click

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.utils.fuzzyfinder import (
    FuzzyFinder,
    FuzzyFinderConfig,
    FuzzyFinderTarget,
)


@click.group(name="workspace", invoke_without_command=True)
@click.option(
    "--config", default=".metagit.yml", help="Path to the metagit definition file"
)
@click.pass_context
def workspace(ctx: click.Context, config: str) -> None:
    """Workspace subcommands"""

    logger = ctx.obj["logger"]
    # If no subcommand is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return

    try:
        config_manager = MetagitConfigManager(config)
        local_config = config_manager.load_config()
        if isinstance(local_config, Exception):
            raise local_config
    except Exception as e:
        logger.error(f"Failed to load metagit definition file: {e}")
        sys.exit(1)
    ctx.obj["local_config"] = local_config


@workspace.command("select")
@click.option(
    "--project",
    default=None,
    help="Project within workspace to select target paths from",
)
@click.pass_context
def workspace_select(ctx: click.Context, project: str = None) -> None:
    """Select workspace project repo to work on"""
    logger = ctx.obj["logger"]
    local_config = ctx.obj["local_config"]
    workspace_project = [
        target_project
        for target_project in local_config.workspace.projects
        if target_project.name == project
    ][0]
    try:
        config = ctx.obj["config"]
        if project is None:
            project: str = config.workspace.default_project
        workspace_path = config.workspace.path
        project_path: str = os.path.join(workspace_path, project)

        if not Path(project_path).exists(follow_symlinks=True):
            logger.warning(f"Project path does not exist for project: {project_path}")
            logger.warning(
                f"You can sync the project with `metagit workspace sync --project {project_path}`"
            )
            return
        else:
            logger.info(f"Project path: {project_path}")
        project_dict = {}
        for f in Path(project_path).iterdir():
            if f.is_dir():
                project_dict[f.name] = "Directory - non-workspace managed"
            if f.is_symlink():
                target_path = f.readlink()
                project_dict[f.name] = f"Symlink({target_path}) - non-workspace managed"
        for repo in workspace_project.repos:
            if repo.name in project_dict.keys():
                target_kind = "Directory"
                if repo.path is not None:
                    target_kind = f"Symlink ({repo.path})"
                if repo.description is None:
                    project_dict[repo.name] = f"{target_kind} - no description"
                else:
                    project_dict[repo.name] = f"{target_kind} - {repo.description}"
        projects: List[FuzzyFinderTarget] = []
        for target in project_dict.keys():
            projects.append(
                FuzzyFinderTarget(name=target, description=project_dict[target])
            )
        if len(projects) == 0:
            logger.warning(f"No projects found in workspace: {project_path}")
            return

        finder_config = FuzzyFinderConfig(
            items=projects,
            prompt_text="🔍 Search projects: ",
            max_results=20,
            score_threshold=60.0,
            highlight_color="bold white bg:#0066cc",
            normal_color="cyan",
            prompt_color="bold green",
            separator_color="gray",
            enable_preview=True,
            display_field="name",
            preview_field="description",
            preview_header="About",
        )
        finder = FuzzyFinder(finder_config)
        selected = finder.run()
        if isinstance(selected, Exception):
            raise selected
        logger.echo(f"Selected: {selected}")
    except Exception as e:
        logger.error(f"Failed to select workspace project: {e}")
        ctx.abort()

"""
Project subcommand
"""

import os
import sys
from pathlib import Path

import click

from metagit.core.appconfig import AppConfig
from metagit.core.config.manager import ConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.project.manager import ProjectManager
from metagit.core.utils.fuzzyfinder import FuzzyFinder, FuzzyFinderConfig
from metagit.core.utils.logging import UnifiedLogger
from metagit.core.workspace.models import WorkspaceProject


@click.group(name="project", invoke_without_command=True)
@click.option(
    "--config", default=".metagit.yml", help="Path to the metagit definition file"
)
@click.option(
    "--project",
    default=None,
    help="Project within workspace to operate on",
)
@click.pass_context
def project(ctx: click.Context, config: str, project: str = None) -> None:
    """Project subcommands"""
    logger = ctx.obj["logger"]
    app_config: AppConfig = ctx.obj["config"]
    try:
        config_manager: ConfigManager = ConfigManager(config)
        local_config: MetagitConfig = config_manager.load_config()
        if isinstance(local_config, Exception):
            raise local_config
    except Exception as e:
        logger.error(f"Failed to load metagit definition file: {e}")
        sys.exit(1)
    ctx.obj["local_config"] = local_config
    if not project:
        project: str = app_config.default_project
    ctx.obj["project"] = project
    # If no subcommand is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return


@project.command("select")
@click.pass_context
def project_select(ctx: click.Context) -> None:
    """Select workspace project repo to work on"""
    logger: UnifiedLogger = ctx.obj["logger"]
    project: str = ctx.obj["project"]
    app_config: AppConfig = ctx.obj["config"]
    try:
        workspace_path = app_config.workspace.path
        project_path: str = os.path.join(workspace_path, project)

        if not Path(project_path).exists(follow_symlinks=True):
            logger.warning(f"Path does not exist for this project: {project_path}")
            logger.warning(
                f"You can sync the project with `metagit workspace sync --project {project_path}`"
            )
            return
        else:
            logger.info(f"Project path: {project_path}")

        repos: list[str] = [f.name for f in Path(project_path).iterdir() if f.is_dir()]
        if len(repos) == 0:
            logger.warning(f"No repos found in project: {project_path}")
            return

        finder_config = FuzzyFinderConfig(
            items=repos,
            prompt_text="🔍 Search repos: ",
            max_results=20,
            score_threshold=70.0,
            highlight_color="bold white bg:#0066cc",
            normal_color="cyan",
            prompt_color="bold green",
            separator_color="gray",
        )
        finder = FuzzyFinder(finder_config)
        selected = finder.run()
        if isinstance(selected, Exception):
            raise selected
        logger.echo(f"Selected: {selected}")
    except Exception as e:
        logger.error(f"Failed to select project repo: {e}")
        ctx.abort()


@project.command("sync")
@click.pass_context
def project_sync(ctx: click.Context) -> None:
    """Sync project within workspace"""
    logger = ctx.obj["logger"]
    app_config: AppConfig = ctx.obj["config"]
    project: str = ctx.obj["project"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    project_manager: ProjectManager = ProjectManager(app_config.workspace.path, logger)
    workspace_project: WorkspaceProject = next(
        p for p in local_config.workspace.projects if p.name == project
    )
    sync_result: bool = project_manager.sync(workspace_project)
    if sync_result:
        logger.info(f"Project {project} synced successfully")
    else:
        logger.error(f"Failed to sync project {project}")
        ctx.abort()

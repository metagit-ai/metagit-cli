"""
Project subcommand
"""

import sys

import click
import yaml

from metagit.core.appconfig import AppConfig
from metagit.core.config.manager import ConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.project.manager import ProjectManager
from metagit.core.utils.logging import UnifiedLogger
from metagit.core.workspace.models import WorkspaceProject
from metagit.cli.commands.project_repo import repo, repo_select
from metagit.core.utils.click import call_click_command_with_ctx

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
    # If no subcommand is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return
    app_config: AppConfig = ctx.obj["config"]
    if not project:
        project: str = app_config.default_project
    ctx.obj["project"] = project
    ctx.obj["config_path"] = config
    try:
        config_manager: ConfigManager = ConfigManager(config)
        local_config: MetagitConfig = config_manager.load_config()
        ctx.obj["local_config"] = local_config
        if isinstance(local_config, Exception):
            raise local_config
    except Exception as e:
        logger.error(f"Failed to load metagit definition file: {e}")
        sys.exit(1)


# Add repo group to project group
project.add_command(repo)


@project.command("list")
@click.pass_context
def project_list(ctx: click.Context) -> None:
    """List the current project configuration in YAML format"""
    logger: UnifiedLogger = ctx.obj["logger"]
    project: str = ctx.obj["project"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    
    try:
        # Find the current project in the workspace
        workspace_project: WorkspaceProject = next(
            (p for p in local_config.workspace.projects if p.name == project), None
        )
        
        if not workspace_project:
            logger.error(f"Project '{project}' not found in workspace configuration")
            ctx.abort()
        
        # Convert the entire WorkspaceProject to YAML and display
        project_dict = workspace_project.model_dump(exclude_none=True)
        yaml_output = yaml.dump(project_dict, default_flow_style=False, sort_keys=False)
        logger.echo(yaml_output)
        
    except Exception as e:
        logger.error(f"Failed to list project: {e}")
        ctx.abort()


@project.command("select")
@click.pass_context
def project_select(ctx: click.Context) -> None:
    """Shortcut: Uses 'project repo select' to select workspace project repo to work on"""
    # Call the repo_select function
    call_click_command_with_ctx(repo_select, ctx)


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

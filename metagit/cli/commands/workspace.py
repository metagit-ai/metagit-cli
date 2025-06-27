"""
Workspace subcommand
"""

import sys

import click

from metagit.cli.commands.project_repo import repo_select
from metagit.core.appconfig import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.utils.click import call_click_command_with_ctx


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
    "-p",
    default=None,
    help="Project within workspace to select target paths from",
)
@click.pass_context
def workspace_select(ctx: click.Context, project: str = None) -> None:
    """Select project repo to work on"""
    app_config: AppConfig = ctx.obj["config"]
    if not project:
        project: str = app_config.workspace.default_project
        ctx.obj["project"] = project
    else:
        ctx.obj["project"] = project
    call_click_command_with_ctx(repo_select, ctx)
    return

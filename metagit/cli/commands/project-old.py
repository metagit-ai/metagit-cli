"""
Project cli command group
"""

import os
import sys
from pathlib import Path

import click

from metagit import DATA_PATH
from metagit.core.config.manager import ConfigManager
from metagit.core.utils.yaml_class import yaml


@click.group(name="project", invoke_without_command=True)
@click.option(
    "--config-path",
    help="Path to the metagit configuration file",
    default=".metagit.yml",
)
@click.pass_context
def project(ctx: click.Context, config_path: str) -> None:
    """Project subcommands"""
    try:
        # If no subcommand is provided, show help
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())
            return
        ctx.obj["config_path"] = config_path
    except Exception as e:
        logger = ctx.obj.get("logger")
        if logger:
            logger.error(f"An error occurred in the project command: {e}")
        else:
            click.echo(f"An error occurred: {e}", err=True)
        ctx.abort()


@project.command("detect")
@click.pass_context
def project_detect(ctx: click.Context) -> None:
    """Run detection for a project"""
    logger = ctx.obj["logger"]
    try:
        config_path = ctx.obj["config_path"]
        config_manager = ConfigManager(config_path=config_path)
        config_result = config_manager.load_config()
        if isinstance(config_result, Exception):
            raise config_result

        yaml.Dumper.ignore_aliases = lambda *args: True
        output = yaml.dump(
            config_result.model_dump(),
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            line_break=True,
        )
        logger.echo(output)
    except Exception as e:
        logger.error(f"Failed to run project detection: {e}")
        logger.debug(f"Error: {e}")
        ctx.abort()


@project.command("sync")
@click.option(
    "--project",
    default=None,
    help="Project within workspace to sync",
)
@click.pass_context
def project_sync(ctx: click.Context, project: str = None) -> None:
    """Sync project within workspace"""
    logger = ctx.obj["logger"]
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
    except Exception as e:
        logger.error(f"Failed to sync project: {e}")
        ctx.abort()


@project.command("create")
@click.option(
    "--output-path",
    help="Path to the metagit configuration file",
    default=None,
)
@click.option("--name", help="Project name")
@click.option(
    "--description",
    help="Project description",
    default="Project description",
)
@click.option(
    "--url",
    help="Project URL",
    default="https://github.com/metagit-io/metagit_detect",
)
@click.option(
    "--kind",
    help="Project kind",
    default="application",
)
@click.pass_context
def config_create(
    ctx, output_path: str, name: str, description: str, url: str, kind: str
):
    """Create default application config"""
    logger = ctx.obj["logger"]
    config = ConfigManager().create_config(
        name=name, description=description, url=url, kind=kind
    )
    yaml.Dumper.ignore_aliases = lambda *args: True
    output = yaml.dump(
        config.model_dump(exclude_unset=True, exclude_none=True),
        default_flow_style=False,
        sort_keys=False,
        indent=2,
        line_break=True,
    )
    if output_path is None:
        logger.echo(output)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(output, f)


@config.command("validate")
@click.pass_context
def config_validate(ctx):
    """Validate metagit configuration"""
    logger = ctx.obj["logger"]
    config_path = ctx.obj["config_path"]
    try:
        _ = ConfigManager(config_path=config_path).load_config()
    except Exception as e:
        logger.error(f"Failed to load metagit configuration file: {e}")
        logger.debug(f"Error: {e}")
        sys.exit(1)

    logger.echo("Configuration is valid")

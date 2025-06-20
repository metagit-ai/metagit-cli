"""
Project cli command group
"""

import os
import sys

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
def project(ctx, config_path: str):
    """Project subcommands"""
    # If no subcommand is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return

    ctx.obj["config_path"] = config_path


@project.command("detect")
@click.pass_context
def project_detect(ctx):
    """Run detection for a project"""
    logger = ctx.obj["logger"]
    config_path = ctx.obj["config_path"]
    try:
        config = ConfigManager(config_path=config_path).load_config()
    except Exception as e:
        logger.error(f"Failed to load metagit configuration file: {e}")
        logger.debug(f"Error: {e}")
        sys.exit(1)

    yaml.Dumper.ignore_aliases = lambda *args: True
    output = yaml.dump(
        config.model_dump(),
        default_flow_style=False,
        sort_keys=False,
        indent=2,
        line_break=True,
    )
    logger.echo(output)


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

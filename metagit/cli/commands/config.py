"""
Config cli command group
"""

import os
import sys

import click

from metagit import DATA_PATH
from metagit.core.config.manager import ConfigManager
from metagit.core.utils.yaml_class import yaml


@click.group(name="config", invoke_without_command=True)
@click.option(
    "--config-path",
    help="Path to the metagit configuration file",
    default=".metagit.yml",
)
@click.pass_context
def config(ctx: click.Context, config_path: str) -> None:
    """Configuration subcommands"""
    try:
        # If no subcommand is provided, show help
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())
            return
        ctx.obj["config_path"] = config_path
    except Exception as e:
        logger = ctx.obj.get("logger")
        if logger:
            logger.error(f"An error occurred in the config command: {e}")
        else:
            click.echo(f"An error occurred: {e}", err=True)
        ctx.abort()


@config.command("show")
@click.pass_context
def config_show(ctx: click.Context) -> None:
    """Show metagit configuration"""
    logger = ctx.obj["logger"]
    try:
        config_path = ctx.obj["config_path"]
        config_manager = ConfigManager(config_path=config_path)
        config_result = config_manager.load_config()
        if isinstance(config_result, Exception):
            raise config_result

        yaml.Dumper.ignore_aliases = lambda *args: True
        output = yaml.dump(
            config_result.model_dump(exclude_unset=True, exclude_none=True),
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            line_break=True,
        )
        logger.echo(output)
    except Exception as e:
        logger.error(f"Failed to load metagit configuration file: {e}")
        logger.debug(f"Error: {e}")
        ctx.abort()


@config.command("create")
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
    ctx: click.Context,
    output_path: str,
    name: str,
    description: str,
    url: str,
    kind: str,
) -> None:
    """Create default application config"""
    logger = ctx.obj["logger"]
    try:
        config_manager = ConfigManager()
        config_result = config_manager.create_config(
            name=name, description=description, url=url, kind=kind
        )
        if isinstance(config_result, Exception):
            raise config_result
        yaml.Dumper.ignore_aliases = lambda *args: True
        output = yaml.dump(
            config_result.model_dump(exclude_unset=True, exclude_none=True),
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            line_break=True,
        )
        if output_path is None:
            logger.echo(output)
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output)
    except Exception as e:
        logger.error(f"Failed to create config: {e}")
        ctx.abort()


@config.command("validate")
@click.pass_context
def config_validate(ctx: click.Context) -> None:
    """Validate metagit configuration"""
    logger = ctx.obj["logger"]
    try:
        config_path = ctx.obj["config_path"]
        config_manager = ConfigManager(config_path=config_path)
        result = config_manager.load_config()
        if isinstance(result, Exception):
            raise result
        logger.echo("Configuration is valid")
    except Exception as e:
        logger.error(f"Failed to load metagit configuration file: {e}")
        logger.debug(f"Error: {e}")
        ctx.abort()

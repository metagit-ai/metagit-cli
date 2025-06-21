"""
Appconfig subcommand
"""

import os
import sys
from typing import Union

import click
import yaml as base_yaml
from pydantic import ValidationError

from metagit import DATA_PATH
from metagit.core.appconfig import AppConfig, get_config, load_config
from metagit.core.utils.yaml_class import yaml


@click.group(name="appconfig", invoke_without_command=True)
@click.pass_context
def appconfig(ctx: click.Context) -> None:
    """Application configuration subcommands"""
    try:
        # If no subcommand is provided, show help
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())
            return
    except Exception as e:
        logger = ctx.obj.get("logger")
        if logger:
            logger.error(f"An error occurred in the appconfig command: {e}")
        else:
            click.echo(f"An error occurred: {e}", err=True)
        ctx.abort()


@appconfig.command("show")
@click.pass_context
def appconfig_show(ctx: click.Context) -> None:
    """Show current configuration"""
    try:
        config = ctx.obj["config"].model_dump()

        config_as_dict = {
            "config": config,
        }
        logger = ctx.obj["logger"]

        base_yaml.Dumper.ignore_aliases = lambda *args: True
        output = base_yaml.dump(
            config_as_dict,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            line_break=True,
        )
        logger.echo(output)
    except Exception as e:
        logger = ctx.obj.get("logger")
        if logger:
            logger.error(f"Failed to show appconfig: {e}")
        else:
            click.echo(f"An error occurred: {e}", err=True)
        ctx.abort()


@appconfig.command("validate")
@click.option("--config-path", help="Path to the configuration file", default=None)
@click.pass_context
def appconfig_validate(
    ctx: click.Context, config_path: Union[str, None] = None
) -> None:
    """Validate a configuration file"""
    logger = ctx.obj["logger"]
    try:
        if not config_path:
            config_path = os.path.join(DATA_PATH, "metagit.config.yaml")
        logger.echo(f"Validating configuration file: {config_path}")

        # Step 1: Load YAML
        with open(config_path) as f:
            from metagit.core.utils.yaml_class import load as yaml_load

            config_data = yaml_load(f)
            if isinstance(config_data, Exception):
                raise config_data
        # Step 2: Validate structure with Pydantic model
        try:
            _ = AppConfig(**config_data["config"])
        except ValidationError as ve:
            logger.error(f"Model validation failed: {ve}")
            sys.exit(1)
        logger.echo("Configuration is valid!")
    except Exception as e:
        logger.error(f"Failed to load or validate config: {e}")
        sys.exit(1)


# @appconfig.command("checksum")
# @click.pass_context
# def appconfig_checksum(ctx):
#     """Checksum of current configuration"""
#     config = Config()
#     config.load(configfile=ctx.appconfigfile)
#     checksum = config.checksum()
#     logger.echo(checksum, console=True)


@appconfig.command("get")
@click.option("--name", default="", help="Appconfig element to target")
@click.option(
    "--show-keys",
    is_flag=True,
    default=False,
    help="If the element is a dictionary, show all key names. If it is a list, show all name attributes",
)
@click.option("--output", default="json", help="Output format (json/yaml)")
@click.pass_context
def appconfig_get(ctx: click.Context, name: str, show_keys: bool, output: str) -> None:
    """Display appconfig value"""
    try:
        config = ctx.obj["config"]
        result = get_config(
            appconfig=config, name=name, show_keys=show_keys, output=output
        )
        if isinstance(result, Exception):
            raise result
    except Exception as e:
        logger = ctx.obj.get("logger")
        if logger:
            logger.error(f"Failed to get appconfig value: {e}")
        else:
            click.echo(f"An error occurred: {e}", err=True)
        ctx.abort()


@appconfig.command("create")
@click.pass_context
def appconfig_create(ctx: click.Context) -> None:
    """Create default application config"""
    try:
        config_result = load_config(
            config_path=os.path.join(DATA_PATH, "metagit.config.yaml")
        )
        if isinstance(config_result, Exception):
            raise config_result
        config: AppConfig = config_result
        base_yaml.Dumper.ignore_aliases = lambda *args: True
        output = base_yaml.dump(
            config.model_dump(),
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            line_break=True,
        )
        print(output)
    except Exception as e:
        logger = ctx.obj.get("logger")
        if logger:
            logger.error(f"Failed to create default appconfig: {e}")
        else:
            click.echo(f"An error occurred: {e}", err=True)
        ctx.abort()

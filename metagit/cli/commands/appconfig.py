"""
Appconfig subcommand
"""

import os
import sys

import click
import yaml as base_yaml
from pydantic import ValidationError

from metagit import DATA_PATH
from metagit.core.appconfig import AppConfig, get_config, load_config
from metagit.core.utils.yaml_class import yaml


@click.group(name="appconfig", invoke_without_command=True)
@click.pass_context
def appconfig(ctx):
    """Application configuration subcommands"""
    # If no subcommand is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return


@appconfig.command("show")
@click.pass_context
def appconfig_show(ctx):
    """Show current configuration"""
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


@appconfig.command("validate")
@click.option("--config-path", help="Path to the configuration file", default=None)
@click.pass_context
def appconfig_validate(ctx, config_path: str = None):
    """Validate a configuration file"""
    logger = ctx.obj["logger"]
    if not config_path:
        config_path = os.path.join(DATA_PATH, "metagit.config.yaml")
    logger.echo(f"Validating configuration file: {config_path}")
    try:
        # Step 1: Load YAML
        with open(config_path) as f:
            config_data = yaml.safe_load(f)
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
def appconfig_get(ctx, name, show_keys, output):
    """Display appconfig value"""
    # logger = ctx.obj["logger"]
    config = ctx.obj["config"]
    get_config(appconfig=config, name=name, show_keys=show_keys, output=output)


@appconfig.command("create")
@click.pass_context
def appconfig_create(ctx):
    """Create default application config"""
    config: AppConfig = load_config(
        config_path=os.path.join(DATA_PATH, "metagit.config.yaml")
    )
    base_yaml.Dumper.ignore_aliases = lambda *args: True
    output = base_yaml.dump(
        config.model_dump(),
        default_flow_style=False,
        sort_keys=False,
        indent=2,
        line_break=True,
    )
    print(output)

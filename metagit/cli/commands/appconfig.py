"""
Appconfig subcommand
"""

import os
import json
import sys
from typing import Union

import click
import yaml as base_yaml
from pydantic import ValidationError

from metagit import DATA_PATH, DEFAULT_CONFIG
from metagit.core.appconfig import get_config, load_config
from metagit.core.appconfig.models import AppConfig
from metagit.core.utils.logging import UnifiedLogger, LoggerConfig
from metagit import __version__


@click.group(name="appconfig", invoke_without_command=True)
@click.pass_context
def appconfig(ctx: click.Context) -> None:
    """Application configuration subcommands"""
    # If no subcommand is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return

@appconfig.command("info")
@click.pass_context
def appconfig_info(ctx: click.Context) -> None:
    """
    Information about the application configuration.
    """
    logger = ctx.obj.get("logger") or UnifiedLogger(LoggerConfig())
    logger.config_element(name="version", value=__version__, console=True)
    logger.config_element(name="config_path", value=ctx.obj["config_path"], console=True)

@appconfig.command("show")
@click.pass_context
def appconfig_show(ctx: click.Context) -> None:
    """Show current configuration"""
    try:
        config = ctx.obj["config"].model_dump(
            exclude_none=True, exclude_defaults=True, mode="json"
        )

        config_as_dict = {
            "config": config,
        }
        logger = ctx.obj["logger"]

        base_yaml.Dumper.ignore_aliases = lambda *args: True  # noqa: ARG005
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


@appconfig.command("get",
help='''
Get a value from the application configuration.\n

Example - show all keys in the providers section:\n
  metagit appconfig get --name config.providers --show-keys\n
Example - show all values in the providers section:\n
  metagit appconfig get --name config.providers
''')
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
@click.option(
    "--config-path",
    help="Path to save configuration file (default: ~/.config/metagit/config.yml).",
    default=os.path.join(os.getcwd(), "metagit.config.yaml"),
)
@click.pass_context
def appconfig_create(ctx: click.Context, config_path: str = None) -> None:
    """Create default application config"""
    logger = ctx.obj.get("logger")
    default_config = load_config(DEFAULT_CONFIG)
    if not os.path.exists(config_path):
        try:
            output = base_yaml.dump(
                default_config.model_dump(
                    exclude_none=True, exclude_defaults=False, mode="json"
                ),
                default_flow_style=False,
                sort_keys=False,
                indent=2,
                line_break=True,
            )
            with open(config_path, "w") as f:
                f.write(output)
            logger.success(f"Configuration file {config_path} created")
        except Exception as e:
            logger.error(f"Failed to create default appconfig: {e}")
            ctx.abort()
    else:
        logger.warning(f"Configuration file {config_path} already exists!")


@appconfig.command("schema")
@click.option(
    "--output-path",
    help="Path to output the JSON schema file",
    default="metagit_appconfig.schema.json",
)
@click.pass_context
def appconfig_schema(ctx: click.Context, output_path: str) -> None:
    """
    Generate a JSON schema for the AppConfig class and write it to a file.
    """
    logger = ctx.obj["logger"]
    try:
        schema = AppConfig.model_json_schema()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2)
        logger.success(f"JSON schema written to {output_path}")
    except Exception as e:
        logger.error(f"Failed to generate JSON schema: {e}")
        ctx.abort()


# @appconfig.command("init")
# @click.option(
#     "--config-path",
#     help="Path to save configuration file (default: ~/.config/metagit/config.yml).",
#     default=os.path.join(os.getcwd(), "metagit.config.yaml"),
# )
# @click.option(
#     "--github-token",
#     help="GitHub API token to include in initial configuration.",
# )
# @click.option(
#     "--gitlab-token",
#     help="GitLab API token to include in initial configuration.",
# )
# @click.pass_context
# def init(
#     ctx: click.Context,
#     github_token: str = None,
#     gitlab_token: str = None,
#     config_path: str = None,
# ) -> None:
#     """Initialize AppConfig with default settings."""
#     logger = ctx.obj["logger"]

#     try:
#         # Create default configuration
#         app_config = AppConfig()

#         # Set tokens if provided
#         if github_token:
#             app_config.providers.github.api_token = github_token
#             app_config.providers.github.enabled = True
#             click.echo("✅ GitHub token configured")

#         if gitlab_token:
#             app_config.providers.gitlab.api_token = gitlab_token
#             app_config.providers.gitlab.enabled = True
#             click.echo("✅ GitLab token configured")

#         # Save configuration
#         result = app_config.save(config_path)
#         if isinstance(result, Exception):
#             logger.error(f"Failed to save configuration: {result}")
#             ctx.abort()

#         click.echo(
#             f"✅ Configuration initialized at: {config_path or '~/.config/metagit/config.yml'}"
#         )
#         click.echo(
#             "You can now use 'metagit config providers --show' to view your configuration."
#         )

#     except Exception as e:
#         logger.error(f"Error initializing configuration: {e}")
#         ctx.abort()

"""
Appconfig subcommand
"""

import json
import os
import sys
from typing import Union

import click
import yaml as base_yaml
from pydantic import ValidationError

from metagit import DATA_PATH, DEFAULT_CONFIG, __version__
from metagit.cli.config_patch_ops import (
    emit_patch_result,
    emit_preview_result,
    emit_tree_result,
    resolve_operations,
)
from metagit.cli.json_output import emit_json
from metagit.core.appconfig import get_config, load_config, save_config, set_config
from metagit.core.appconfig.display import render_appconfig_show
from metagit.core.appconfig.models import AppConfig
from metagit.core.config.patch_service import ConfigPatchService
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger


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
    logger.config_element(
        name="config_path", value=ctx.obj["config_path"], console=True
    )


@appconfig.command("show")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["yaml", "json", "minimal-yaml"], case_sensitive=False),
    default="yaml",
    show_default=True,
    help="Output format (yaml=full active config, json=agents, minimal-yaml=non-default only)",
)
@click.pass_context
def appconfig_show(ctx: click.Context, output_format: str) -> None:
    """Show the full active application configuration."""
    logger = ctx.obj["logger"]
    try:
        config: AppConfig = ctx.obj["config"]
        config_path: str = ctx.obj["config_path"]
        minimal = output_format == "minimal-yaml"
        if output_format == "json":
            from metagit.core.appconfig.display import build_appconfig_payload

            emit_json(
                build_appconfig_payload(
                    config,
                    config_path=config_path,
                    minimal=minimal,
                )
            )
            return
        rendered = render_appconfig_show(
            config,
            config_path=config_path,
            output_format="yaml",
            minimal=minimal,
        )
        click.echo(rendered, nl=False)
    except Exception as e:
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


@appconfig.command(
    "get",
    help="""
Get a value from the application configuration.\n
Example - show all keys in the providers section:\n
  metagit appconfig get --name config.providers --show-keys\n
Example - show all values in the providers section:\n
  metagit appconfig get --name config.providers
""",
)
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
                {
                    "config": default_config.model_dump(
                        exclude_none=True, exclude_defaults=False, mode="json"
                    )
                },
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


@appconfig.command("set")
@click.option("--name", help="Appconfig element to target")
@click.option("--value", help="Value to set")
@click.pass_context
def appconfig_set(ctx: click.Context, name: str, value: str) -> None:
    """Set a value in the application configuration."""
    logger = ctx.obj.get("logger") or UnifiedLogger(LoggerConfig())
    try:
        config = ctx.obj["config"]
        config_path = ctx.obj["config_path"]

        updated_config = set_config(appconfig=config, name=name, value=value)
        if isinstance(updated_config, Exception):
            raise updated_config

        save_result = save_config(config_path=config_path, config=updated_config)
        if isinstance(save_result, Exception):
            raise save_result

        logger.success(f"Updated '{name}' to '{value}' in {config_path}")

    except Exception as e:
        if logger:
            logger.error(f"Failed to set appconfig value: {e}")
        else:
            click.echo(f"An error occurred: {e}", err=True)
        ctx.abort()


@appconfig.command("tree")
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Print JSON for agents"
)
@click.pass_context
def appconfig_tree(ctx: click.Context, as_json: bool) -> None:
    """Show schema-backed field tree for metagit.config.yaml."""
    logger = ctx.obj["logger"]
    config_path = ctx.obj["config_path"]
    result = ConfigPatchService().build_tree("appconfig", config_path)
    if isinstance(result, Exception):
        logger.error(f"Failed to build appconfig tree: {result}")
        ctx.abort()
    emit_tree_result(result, as_json=as_json)


@appconfig.command("preview")
@click.option(
    "--style",
    type=click.Choice(["normalized", "minimal", "disk"], case_sensitive=False),
    default="normalized",
    show_default=True,
    help="YAML preview style",
)
@click.option(
    "--file",
    "operations_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="JSON file with operations array or {operations, save}",
)
@click.option(
    "--op",
    type=click.Choice(["enable", "disable", "set", "append", "remove"]),
    default=None,
    help="Single operation kind (use with --path)",
)
@click.option("--path", default=None, help="Field path for a single operation")
@click.option("--value", default=None, help="Value for set (JSON or scalar)")
@click.option(
    "--output",
    "output_path",
    default=None,
    help="Write preview YAML to this path instead of stdout",
)
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Print JSON for agents"
)
@click.pass_context
def appconfig_preview(
    ctx: click.Context,
    style: str,
    operations_file: str | None,
    op: str | None,
    path: str | None,
    value: str | None,
    output_path: str | None,
    as_json: bool,
) -> None:
    """Preview app config after draft operations (secrets redacted in output)."""
    logger = ctx.obj["logger"]
    config_path = ctx.obj["config_path"]
    operations = (
        resolve_operations(
            operations_file=operations_file,
            op=op,
            path=path,
            value=value,
        )
        if operations_file or op
        else []
    )
    result = ConfigPatchService().preview(
        "appconfig",
        config_path,
        operations,
        style=style,
    )
    if isinstance(result, Exception):
        logger.error(f"Failed to preview appconfig: {result}")
        ctx.abort()
    emit_preview_result(
        result,
        as_json=as_json,
        logger=logger,
        output_path=output_path,
    )


@appconfig.command("patch")
@click.option(
    "--file",
    "operations_file",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="JSON file with operations array or {operations, save}",
)
@click.option(
    "--op",
    type=click.Choice(["enable", "disable", "set", "append", "remove"]),
    default=None,
    help="Single operation kind (use with --path)",
)
@click.option("--path", default=None, help="Field path for a single operation")
@click.option("--value", default=None, help="Value for set (JSON or scalar)")
@click.option(
    "--save",
    is_flag=True,
    default=False,
    help="Write changes to disk when validation passes",
)
@click.option(
    "--tree",
    "include_tree",
    is_flag=True,
    default=False,
    help="Include updated schema tree in JSON output",
)
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Print JSON for agents"
)
@click.pass_context
def appconfig_patch(
    ctx: click.Context,
    operations_file: str | None,
    op: str | None,
    path: str | None,
    value: str | None,
    save: bool,
    include_tree: bool,
    as_json: bool,
) -> None:
    """
    Apply schema operations to metagit.config.yaml (enable/disable/set/append/remove).

    Paths use AppConfig field names (e.g. workspace.dedupe.enabled), not the config: wrapper.
    """
    logger = ctx.obj["logger"]
    config_path = ctx.obj["config_path"]
    operations = resolve_operations(
        operations_file=operations_file,
        op=op,
        path=path,
        value=value,
    )
    result = ConfigPatchService().patch(
        "appconfig",
        config_path,
        operations,
        save=save,
        include_tree=include_tree or as_json,
        mask_secrets=True,
    )
    if isinstance(result, Exception):
        logger.error(f"Failed to patch appconfig: {result}")
        ctx.abort()
    emit_patch_result(result, as_json=as_json, logger=logger)


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

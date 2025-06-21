"""
Workspace subcommand
"""

import os
import sys
from pathlib import Path

import click

from metagit.core.config.manager import ConfigManager
from metagit.core.utils.fuzzyfinder import FuzzyFinder, FuzzyFinderConfig


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
        config_manager = ConfigManager(config)
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
    default=None,
    help="Project within workspace to select target paths from",
)
@click.pass_context
def workspace_select(ctx: click.Context, project: str = None) -> None:
    """Select workspace project repo to work on"""
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

        projects: list[str] = [
            f.name for f in Path(project_path).iterdir() if f.is_dir()
        ]
        if len(projects) == 0:
            logger.warning(f"No projects found in workspace: {project_path}")
            return

        finder_config = FuzzyFinderConfig(
            items=projects,
            prompt_text="🔍 Search projects: ",
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
        logger.error(f"Failed to select workspace project: {e}")
        ctx.abort()


# @workspace.command("info")
# @click.pass_context
# def workspace_show(ctx):
#     """Show current workspace"""
#     config = ctx.obj["config"].model_dump()

#     config_as_dict = {
#         "config": config,
#     }
#     logger = ctx.obj["logger"]

#     base_yaml.Dumper.ignore_aliases = lambda *args: True
#     output = base_yaml.dump(
#         config_as_dict,
#         default_flow_style=False,
#         sort_keys=False,
#         indent=2,
#         line_break=True,
#     )
#     logger.echo(output)


# @workspace.command("validate")
# @click.option("--config-path", help="Path to the configuration file", default=None)
# @click.pass_context
# def workspace_validate(ctx, config_path: str = None):
#     """Validate a configuration file"""
#     logger = ctx.obj["logger"]
#     if not config_path:
#         config_path = os.path.join(DATA_PATH, "metagit.config.yaml")
#     logger.echo(f"Validating configuration file: {config_path}")
#     try:
#         # Step 1: Load YAML
#         with open(config_path) as f:
#             config_data = yaml.safe_load(f)
#         # Step 2: Validate structure with Pydantic model
#         try:
#             _ = Config(**config_data["config"])
#         except ValidationError as ve:
#             logger.error(f"Model validation failed: {ve}")
#             sys.exit(1)
#         logger.echo("Configuration is valid!")
#     except Exception as e:
#         logger.error(f"Failed to load or validate config: {e}")
#         sys.exit(1)


# @workspace.command("get")
# @click.option("--name", default="", help="Appconfig element to target")
# @click.option(
#     "--show-keys",
#     is_flag=True,
#     default=False,
#     help="If the element is a dictionary, show all key names. If it is a list, show all name attributes",
# )
# @click.option("--output", default="json", help="Output format (json/yaml)")
# @click.pass_context
# def workspace_get(ctx, name, show_keys, output):
#     """Display workspace value"""
#     # logger = ctx.obj["logger"]
#     config = ctx.obj["config"]
#     get_config(workspace=config, name=name, show_keys=show_keys, output=output)


# @workspace.command("create")
# @click.pass_context
# def workspace_create(ctx):
#     """Create default application config"""
#     config: Config = load_config(
#         config_path=os.path.join(DATA_PATH, "metagit.config.yaml")
#     )
#     base_yaml.Dumper.ignore_aliases = lambda *args: True
#     output = base_yaml.dump(
#         config.model_dump(),
#         default_flow_style=False,
#         sort_keys=False,
#         indent=2,
#         line_break=True,
#     )
#     print(output)

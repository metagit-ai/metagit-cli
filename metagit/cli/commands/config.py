"""
Config cli command group
"""

import click

from metagit.core.appconfig import AppConfig
from metagit.core.config.manager import ConfigManager, create_metagit_config
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
@click.option("--name", help="Project name", default=None)
@click.option(
    "--description",
    help="Project description",
    default=None,
)
@click.option(
    "--url",
    help="Project URL",
    default=None,
)
@click.option(
    "--kind",
    help="Project kind",
    default=None,
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
    """Create metagit config files"""
    logger = ctx.obj["logger"]

    try:
        config_file = create_metagit_config(
            name=name, description=description, url=url, kind=kind, as_yaml=True
        )
        if isinstance(config_file, Exception):
            raise config_file
    except Exception as e:
        logger.error(f"Failed to create config: {e}")
        ctx.abort()

    if output_path is None:
        logger.echo(config_file)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(config_file)


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


@config.command("providers")
@click.option(
    "--show",
    is_flag=True,
    default=False,
    help="Show current provider configuration.",
)
@click.option(
    "--enable-github",
    is_flag=True,
    default=False,
    help="Enable GitHub provider.",
)
@click.option(
    "--disable-github",
    is_flag=True,
    default=False,
    help="Disable GitHub provider.",
)
@click.option(
    "--enable-gitlab",
    is_flag=True,
    default=False,
    help="Enable GitLab provider.",
)
@click.option(
    "--disable-gitlab",
    is_flag=True,
    default=False,
    help="Disable GitLab provider.",
)
@click.option(
    "--github-token",
    help="Set GitHub API token.",
)
@click.option(
    "--gitlab-token",
    help="Set GitLab API token.",
)
@click.option(
    "--github-url",
    help="Set GitHub API base URL (for GitHub Enterprise).",
)
@click.option(
    "--gitlab-url",
    help="Set GitLab API base URL (for self-hosted GitLab).",
)
@click.option(
    "--config-path",
    help="Path to configuration file (default: ~/.config/metagit/config.yml).",
)
@click.pass_context
def providers(
    ctx: click.Context,
    show: bool,
    enable_github: bool,
    disable_github: bool,
    enable_gitlab: bool,
    disable_gitlab: bool,
    github_token: str,
    gitlab_token: str,
    github_url: str,
    gitlab_url: str,
    config_path: str,
) -> None:
    """Manage git provider plugin configuration."""
    logger = ctx.obj["logger"]

    try:
        # Load current configuration
        app_config = AppConfig.load(config_path)
        if isinstance(app_config, Exception):
            logger.error(f"Failed to load configuration: {app_config}")
            ctx.abort()

        # Show current configuration
        if show:
            click.echo("Current Provider Configuration:")
            click.echo(
                f"  GitHub: {'Enabled' if app_config.providers.github.enabled else 'Disabled'}"
            )
            if app_config.providers.github.api_token:
                click.echo(
                    f"    Token: {'*' * 10}{app_config.providers.github.api_token[-4:]}"
                )
            else:
                click.echo("    Token: Not set")
            click.echo(f"    Base URL: {app_config.providers.github.base_url}")

            click.echo(
                f"  GitLab: {'Enabled' if app_config.providers.gitlab.enabled else 'Disabled'}"
            )
            if app_config.providers.gitlab.api_token:
                click.echo(
                    f"    Token: {'*' * 10}{app_config.providers.gitlab.api_token[-4:]}"
                )
            else:
                click.echo("    Token: Not set")
            click.echo(f"    Base URL: {app_config.providers.gitlab.base_url}")
            return

        # Update configuration
        modified = False

        # GitHub configuration
        if enable_github:
            app_config.providers.github.enabled = True
            modified = True
            click.echo("✅ GitHub provider enabled")

        if disable_github:
            app_config.providers.github.enabled = False
            modified = True
            click.echo("✅ GitHub provider disabled")

        if github_token:
            app_config.providers.github.api_token = github_token
            modified = True
            click.echo("✅ GitHub token updated")

        if github_url:
            app_config.providers.github.base_url = github_url
            modified = True
            click.echo("✅ GitHub base URL updated")

        # GitLab configuration
        if enable_gitlab:
            app_config.providers.gitlab.enabled = True
            modified = True
            click.echo("✅ GitLab provider enabled")

        if disable_gitlab:
            app_config.providers.gitlab.enabled = False
            modified = True
            click.echo("✅ GitLab provider disabled")

        if gitlab_token:
            app_config.providers.gitlab.api_token = gitlab_token
            modified = True
            click.echo("✅ GitLab token updated")

        if gitlab_url:
            app_config.providers.gitlab.base_url = gitlab_url
            modified = True
            click.echo("✅ GitLab base URL updated")

        # Save configuration if modified
        if modified:
            result = app_config.save(config_path)
            if isinstance(result, Exception):
                logger.error(f"Failed to save configuration: {result}")
                ctx.abort()
            click.echo("✅ Configuration saved")
        else:
            click.echo("No changes made. Use --show to view current configuration.")

    except Exception as e:
        logger.error(f"Error managing provider configuration: {e}")
        ctx.abort()


@config.command("init")
@click.option(
    "--config-path",
    help="Path to save configuration file (default: ~/.config/metagit/config.yml).",
)
@click.option(
    "--github-token",
    help="GitHub API token to include in initial configuration.",
)
@click.option(
    "--gitlab-token",
    help="GitLab API token to include in initial configuration.",
)
@click.pass_context
def init(
    ctx: click.Context,
    config_path: str,
    github_token: str,
    gitlab_token: str,
) -> None:
    """Initialize AppConfig with default settings."""
    logger = ctx.obj["logger"]

    try:
        # Create default configuration
        app_config = AppConfig()

        # Set tokens if provided
        if github_token:
            app_config.providers.github.api_token = github_token
            app_config.providers.github.enabled = True
            click.echo("✅ GitHub token configured")

        if gitlab_token:
            app_config.providers.gitlab.api_token = gitlab_token
            app_config.providers.gitlab.enabled = True
            click.echo("✅ GitLab token configured")

        # Save configuration
        result = app_config.save(config_path)
        if isinstance(result, Exception):
            logger.error(f"Failed to save configuration: {result}")
            ctx.abort()

        click.echo(
            f"✅ Configuration initialized at: {config_path or '~/.config/metagit/config.yml'}"
        )
        click.echo(
            "You can now use 'metagit config providers --show' to view your configuration."
        )

    except Exception as e:
        logger.error(f"Error initializing configuration: {e}")
        ctx.abort()

"""
Detect subcommand
"""

import json
import os

import click
import yaml

from metagit.core.detect.manager import DetectionManager, DetectionManagerConfig
from metagit.core.providers import registry
from metagit.core.providers.github import GitHubProvider
from metagit.core.providers.gitlab import GitLabProvider


@click.group(name="detect", invoke_without_command=True, help="Detection subcommands")
@click.pass_context
def detect(ctx: click.Context) -> None:
    """Detection subcommands"""
    # If no subcommand is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return


@detect.command("repo")
@click.option(
    "--path",
    "-p",
    default="./",
    show_default=True,
    help="Path to the git repository to analyze.",
)
@click.option(
    "--output",
    "-o",
    default="yaml",
    show_default=True,
    help="Output format (yaml, json, summary).",
)
@click.pass_context
def detect_repo(ctx: click.Context, path: str, output: str) -> None:
    """Detect the codebase."""
    logger = ctx.obj["logger"]
    try:
        # Create DetectionManager with all analyses enabled
        config = DetectionManagerConfig.all_enabled()
        project = DetectionManager.from_path(path, logger, config)
        if isinstance(project, Exception):
            raise project

        run_result = project.run_all()
        if isinstance(run_result, Exception):
            raise run_result

        if output == "yaml":
            yaml_output = project.to_yaml()
            if isinstance(yaml_output, Exception):
                raise yaml_output
            click.echo(yaml_output)
        elif output == "json":
            json_output = project.to_json()
            if isinstance(json_output, Exception):
                raise json_output
            click.echo(json_output)
        else:
            summary_output = project.summary()
            if isinstance(summary_output, Exception):
                raise summary_output
            click.echo(summary_output)
    except Exception as e:
        logger.error(f"Error analyzing project at {path}: {e}")
        ctx.abort()


@detect.command("repository")
@click.option(
    "--path",
    "-p",
    help="Path to local repository to analyze.",
)
@click.option(
    "--url",
    help="URL of remote git repository to clone and analyze.",
)
@click.option(
    "--output",
    "-o",
    default="summary",
    show_default=True,
    type=click.Choice(
        [
            "summary",
            "yaml",
            "json",
            "record",
            "metagit",
            "metagitconfig",
            "summary",
            "all",
        ]
    ),
    help="Output format. Defaults to 'summary'",
)
@click.option(
    "--save",
    "-s",
    is_flag=True,
    default=False,
    help="Save the generated configuration to .metagit.yml in the repository path.",
)
@click.option(
    "--temp-dir",
    help="Temporary directory for cloning remote repositories.",
)
@click.option(
    "--github-token",
    envvar="GITHUB_TOKEN",
    help="GitHub API token for fetching repository metrics (overrides AppConfig).",
)
@click.option(
    "--gitlab-token",
    envvar="GITLAB_TOKEN",
    help="GitLab API token for fetching repository metrics (overrides AppConfig).",
)
@click.option(
    "--github-url",
    envvar="GITHUB_URL",
    help="GitHub API base URL (for GitHub Enterprise, overrides AppConfig).",
)
@click.option(
    "--gitlab-url",
    envvar="GITLAB_URL",
    help="GitLab API base URL (for self-hosted GitLab, overrides AppConfig).",
)
@click.option(
    "--use-app-config",
    is_flag=True,
    default=True,
    help="Use AppConfig for provider configuration (default: True).",
)
@click.option(
    "--config-path",
    default=".metagit.yml",
    help="Path to the MetagitConfig file to save.",
)
@click.pass_context
def detect_repository(
    ctx: click.Context,
    path: str,
    url: str,
    output: str,
    save: bool,
    temp_dir: str,
    github_token: str,
    gitlab_token: str,
    github_url: str,
    gitlab_url: str,
    use_app_config: bool,
    config_path: str,
) -> None:
    """Comprehensive repository analysis and MetagitConfig generation using DetectionManager."""
    logger = ctx.obj["logger"]
    app_config = ctx.obj["config"]
    try:
        # Configure providers
        if use_app_config:
            # Try to load AppConfig and configure providers
            try:
                # app_config = AppConfig.load()
                registry.configure_from_app_config(app_config)
                logger.debug("Configured providers from AppConfig")
            except Exception as e:
                logger.warning(f"Failed to load AppConfig: {e}")
                # Fall back to environment variables
                registry.configure_from_environment()
                logger.debug("Configured providers from environment variables")
        else:
            # Use environment variables only
            registry.configure_from_environment()
            logger.debug("Configured providers from environment variables")

        # Override with CLI options if provided
        if github_token or gitlab_token or github_url or gitlab_url:
            # Clear existing providers and configure with CLI options
            registry.clear()

            if github_token:
                github_provider = GitHubProvider(
                    api_token=github_token,
                    base_url=github_url or "https://api.github.com",
                )
                registry.register(github_provider)
                logger.debug("GitHub provider configured from CLI options")

            if gitlab_token:
                gitlab_provider = GitLabProvider(
                    api_token=gitlab_token,
                    base_url=gitlab_url or "https://gitlab.com/api/v4",
                )
                registry.register(gitlab_provider)
                logger.debug("GitLab provider configured from CLI options")

        # Log configured providers
        providers = registry.get_all_providers()
        if providers:
            provider_names = [p.get_name() for p in providers]
            logger.debug(f"Configured providers: {', '.join(provider_names)}")
        else:
            logger.debug("No providers configured - will use git-based metrics")

        if not path and not url:
            # Default to current directory if no path or URL provided
            path = os.getcwd()
            logger.debug(f"No path or URL provided, using current directory: {path}")

        if path and url:
            logger.error("Please provide either --path or --url, not both.")
            ctx.abort()

        # if not output and not save:
        #     output = "summary"

        # Create DetectionManager with all analyses enabled
        config = DetectionManagerConfig.all_enabled()

        if path:
            logger.debug(f"Analyzing local repository at: {path}")
            detection_manager = DetectionManager.from_path(path, logger, config)
        elif url:
            logger.debug(f"Cloning and analyzing remote repository: {url}")
            detection_manager = DetectionManager.from_url(url, temp_dir, logger, config)

        if isinstance(detection_manager, Exception):
            raise detection_manager

        # Run all analyses
        run_result = detection_manager.run_all()
        if isinstance(run_result, Exception):
            raise run_result

        result = None

        if output == "all":
            # Output all detection data including MetagitRecord fields
            try:
                result = detection_manager.model_dump(
                    exclude_none=True, exclude_defaults=True, mode="json"
                )
                if isinstance(result, Exception):
                    raise result
                result = yaml.safe_dump(
                    result, default_flow_style=False, sort_keys=False, indent=2
                )
                if isinstance(result, Exception):
                    raise result
            except Exception as e:
                logger.error(f"Error dumping detection data: {e}")
                ctx.abort()
        elif output in ["record"]:
            result = detection_manager.to_yaml()
            if isinstance(result, Exception):
                raise result
        elif output in ["metagit", "metagitconfig"]:
            # Convert to MetagitConfig (remove detection-specific fields)
            config_data = detection_manager.model_dump(
                exclude={
                    "detection_config",
                    "branch_analysis",
                    "ci_config_analysis",
                    "directory_summary",
                    "directory_details",
                    "repository_analysis",
                    "logger",
                    "_analysis_completed",
                    "detection_timestamp",
                    "detection_source",
                    "detection_version",
                    "tenant_id",
                }
            )
            result = yaml.safe_dump(
                config_data, default_flow_style=False, sort_keys=False, indent=2
            )
        elif output == "summary":
            result = detection_manager.summary()
            if isinstance(result, Exception):
                raise result
        elif output == "yaml":
            result = yaml.dump(
                detection_manager.model_dump(exclude_none=True, exclude_defaults=True),
                default_flow_style=False,
                sort_keys=False,
                indent=2,
            )
        elif output == "json":
            result = json.dumps(
                detection_manager.model_dump(exclude_none=True, exclude_defaults=True),
                indent=2,
            )

        if not save:
            click.echo(result)
        else:
            if os.path.exists(config_path) and not click.confirm(
                f"Configuration file at '{config_path}' already exists. Do you want to overwrite it?"
            ):
                click.echo("Save operation aborted.")
                if hasattr(detection_manager, "cleanup"):
                    detection_manager.cleanup()
                return

            # Save as MetagitConfig (not DetectionManager)
            config_data = detection_manager.model_dump(
                exclude={
                    "detection_config",
                    "branch_analysis",
                    "ci_config_analysis",
                    "directory_summary",
                    "directory_details",
                    "repository_analysis",
                    "logger",
                    "_analysis_completed",
                    "detection_timestamp",
                    "detection_source",
                    "detection_version",
                    "tenant_id",
                }
            )

            with open(config_path, "w") as f:
                yaml.dump(
                    config_data,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2,
                )
            logger.info(f"✅ MetagitConfig saved to: {config_path}")

        # Clean up if this was a cloned repository
        if hasattr(detection_manager, "cleanup"):
            detection_manager.cleanup()

    except Exception as e:
        logger.error(f"Error during repository analysis: {e}")
        ctx.abort()

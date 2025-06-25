"""
Detect cli command group
"""

import json
import os

import click
import yaml

from metagit.core.appconfig import AppConfig
from metagit.core.detect.manager import DetectionManager
from metagit.core.detect.repository import RepositoryAnalysis
from metagit.core.providers import registry
from metagit.core.providers.github import GitHubProvider
from metagit.core.providers.gitlab import GitLabProvider


@click.group(name="detect", invoke_without_command=True)
@click.pass_context
def detect(ctx: click.Context) -> None:
    """Detection subcommands"""
    # If no subcommand is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return


@detect.command("repo")
@click.option(
    "--repo-path",
    default="./",
    show_default=True,
    help="Path to the git repository to analyze.",
)
@click.option(
    "--output",
    default="yaml",
    show_default=True,
    help="Output format.",
)
@click.pass_context
def repo(ctx: click.Context, repo_path: str, output: str) -> None:
    """Detect the codebase."""
    logger = ctx.obj["logger"]
    try:
        project = DetectionManager(path=repo_path, logger=logger)
        project.config.all_enabled()

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
        logger.error(f"Error analyzing project at {repo_path}: {e}")
        ctx.abort()


@detect.command("repository")
@click.option(
    "--path",
    help="Path to local repository to analyze.",
)
@click.option(
    "--url",
    help="URL of remote git repository to clone and analyze.",
)
@click.option(
    "--output",
    default=None,
    show_default=True,
    type=click.Choice(
        ["summary", "yaml", "json", "record", "metagit", "metagitconfig"]
    ),
    help="Output format. Defaults to 'summary'",
)
@click.option(
    "--save",
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
def repository(
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
    """Comprehensive repository analysis and MetagitConfig generation."""
    logger = ctx.obj["logger"]

    try:
        # Configure providers
        if use_app_config:
            # Try to load AppConfig and configure providers
            try:
                app_config = AppConfig.load()
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

        if not output and not save:
            output = "summary"

        analysis = None

        if path:
            logger.debug(f"Analyzing local repository at: {path}")
            analysis = RepositoryAnalysis.from_path(path, logger)
        elif url:
            logger.debug(f"Cloning and analyzing remote repository: {url}")
            analysis = RepositoryAnalysis.from_url(url, logger, temp_dir)

        if isinstance(analysis, Exception):
            raise analysis

        config = None
        if output in ["record"]:
            result = analysis.to_metagit_record().to_yaml()
            if isinstance(result, Exception):
                raise result

        if output in ["metagit", "metagitconfig"]:
            result = analysis.to_metagit_config().to_yaml()
            if isinstance(result, Exception):
                raise result

        if output == "summary":
            result = analysis.summary()
            if isinstance(result, Exception):
                raise result

        elif output == "yaml":
            result = yaml.dump(
                analysis.model_dump(exclude_none=True, exclude_defaults=True),
                default_flow_style=False,
                sort_keys=False,
                indent=2,
            )

        elif output == "json":
            result = json.dumps(
                config.model_dump(exclude_none=True, exclude_defaults=True), indent=2
            )

        if not save:
            click.echo(result)
        else:
            if os.path.exists(config_path):
                if not click.confirm(
                    f"Configuration file at '{config_path}' already exists. Do you want to overwrite it?"
                ):
                    click.echo("Save operation aborted.")
                    if analysis.is_cloned:
                        analysis.cleanup()
                    return

            with open(config_path, "w") as f:
                yaml.dump(
                    config.model_dump(exclude_none=True, exclude_defaults=True),
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2,
                )
            logger.info(f"✅ MetagitConfig saved to: {config_path}")

        # Clean up if this was a cloned repository
        if analysis.is_cloned:
            analysis.cleanup()

    except Exception as e:
        logger.error(f"Error during repository analysis: {e}")
        ctx.abort()

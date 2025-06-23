"""
Detect cli command group
"""

import click
import tempfile
import os

from metagit.core.detect.project import ProjectAnalysis
from metagit.core.detect.repository import RepositoryAnalysis


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
        logger.debug("Detecting the codebase...")
        project = ProjectAnalysis(path=repo_path, logger=logger)
        logger.debug(f"Analyzing project at: {repo_path}")

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
    type=click.Choice(["summary", "yaml", "json"]),
    help="Output format. Defaults to 'summary' if --save is not used.",
)
@click.option(
    "--save",
    is_flag=True,
    default=False,
    help="Save the generated configuration to .metagit.yml in the repository path."
)
@click.option(
    "--temp-dir",
    help="Temporary directory for cloning remote repositories.",
)
@click.pass_context
def repository(ctx: click.Context, path: str, url: str, output: str, save: bool, temp_dir: str) -> None:
    """Comprehensive repository analysis and MetagitConfig generation."""
    logger = ctx.obj["logger"]
    
    try:
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
        if output in ["yaml", "json"] or save:
            config = analysis.to_metagit_config()
            if isinstance(config, Exception):
                raise config
        
        # Generate output based on format
        if output == "summary":
            summary = analysis.summary()
            if isinstance(summary, Exception):
                raise summary
            click.echo(summary)
        
        elif output == "yaml":
            import yaml
            yaml_output = yaml.dump(
                config.model_dump(exclude_none=True, exclude_defaults=True),
                default_flow_style=False,
                sort_keys=False,
                indent=2
            )
            click.echo(yaml_output)
        
        elif output == "json":
            import json
            json_output = json.dumps(
                config.model_dump(exclude_none=True, exclude_defaults=True),
                indent=2
            )
            click.echo(json_output)
        
        if save:
            config_path = os.path.join(analysis.path, ".metagit.yml")
            if os.path.exists(config_path):
                if not click.confirm(f"Configuration file at '{config_path}' already exists. Do you want to overwrite it?"):
                    click.echo("Save operation aborted.")
                    if analysis.is_cloned:
                        analysis.cleanup()
                    return

            import yaml
            with open(config_path, 'w') as f:
                yaml.dump(
                    config.model_dump(exclude_none=True, exclude_defaults=True),
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2
                )
            logger.info(f"✅ MetagitConfig saved to: {config_path}")
        
        # Clean up if this was a cloned repository
        if analysis.is_cloned:
            analysis.cleanup()
            
    except Exception as e:
        logger.error(f"Error during repository analysis: {e}")
        ctx.abort()

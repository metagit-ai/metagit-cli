"""
Detect cli command group
"""

import click

from metagit.core.detect.project import ProjectAnalysis


@click.group(name="detect", invoke_without_command=True)
@click.pass_context
def detect(ctx):
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
def repo(ctx, repo_path: str, output: str):
    """Detect the codebase."""
    logger = ctx.obj["logger"]
    logger.debug("Detecting the codebase...")
    project = ProjectAnalysis(path=repo_path, logger=logger)
    logger.debug(f"Analyzing project at: {repo_path}")
    try:
        project.run_all()
    except Exception as e:
        logger.error(f"Error analyzing project at {repo_path}: {e}")
        return
    if output == "yaml":
        click.echo(project.to_yaml())
    elif output == "json":
        click.echo(project.to_json())
    else:
        click.echo(project.summary())

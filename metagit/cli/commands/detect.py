"""
Detect cli command group
"""

import click

from metagit.core.repository.project import ProjectAnalysis


@click.group(name="detect", invoke_without_command=True)
@click.pass_context
def detect(ctx: click.Context) -> None:
    """Detection subcommands"""
    try:
        # If no subcommand is provided, show help
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())
            return
    except Exception as e:
        logger = ctx.obj.get("logger")
        if logger:
            logger.error(f"An error occurred in the detect command: {e}")
        else:
            click.echo(f"An error occurred: {e}", err=True)
        ctx.abort()


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

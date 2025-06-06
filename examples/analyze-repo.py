#!/usr/bin/env python
# -*- coding: utf-8 -*-

import click

from src.git_project import ProjectAnalysis
from src.utils.logging import LoggerConfig, UnifiedLogger

logger = UnifiedLogger(LoggerConfig()).get_logger()


@click.command()
@click.option(
    "--repo-path",
    default="./",
    show_default=True,
    help="Path to the git repository to analyze.",
)
def main(repo_path: str):
    project = ProjectAnalysis(path=repo_path, logger=logger)
    logger.debug(f"Analyzing project at: {repo_path}")
    try:
        project.run_all()
    except Exception as e:
        logger.error(f"Error analyzing project at {repo_path}: {e}")
        return
    # print(project.summary())
    click.echo(project.to_yaml())


if __name__ == "__main__":
    main()

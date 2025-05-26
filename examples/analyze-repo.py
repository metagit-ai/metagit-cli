#!/usr/bin/env python
# -*- coding: utf-8 -*-

import click

from src.git_project import ProjectAnalysis


@click.command()
@click.option(
    "--repo-path",
    default="./",
    show_default=True,
    help="Path to the git repository to analyze.",
)
def main(repo_path: str):
    project = ProjectAnalysis(path=repo_path)
    project.run_all()
    print(project.summary())


if __name__ == "__main__":
    main()

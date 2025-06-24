#!/usr/bin/env python
"""
Project repository subcommand
"""

import os
from pathlib import Path
from typing import Optional

import click

from metagit.core.appconfig import AppConfig
from metagit.core.project.manager import ProjectManager
from metagit.core.project.models import ProjectKind, ProjectPath
from metagit.core.utils.common import open_editor
from metagit.core.utils.fuzzyfinder import FuzzyFinder, FuzzyFinderConfig
from metagit.core.utils.logging import UnifiedLogger


@click.group(name="repo")
@click.pass_context
def repo(ctx: click.Context) -> None:
    """Repository subcommands"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return


@repo.command("select")
@click.pass_context
def repo_select(ctx: click.Context) -> None:
    """Select workspace project repo to work on"""
    logger: UnifiedLogger = ctx.obj["logger"]
    project: str = ctx.obj["project"]
    app_config: AppConfig = ctx.obj["config"]
    try:
        workspace_path = app_config.workspace.path
        project_path: str = os.path.join(workspace_path, project)

        if not Path(project_path).exists(follow_symlinks=True):
            logger.warning(f"Path does not exist for this project: {project_path}")
            logger.warning(
                f"You can sync the project with `metagit workspace sync --project {project_path}`"
            )
            return
        else:
            logger.info(f"Project path: {project_path}")

        repos: list[str] = [f.name for f in Path(project_path).iterdir() if f.is_dir()]
        if len(repos) == 0:
            logger.warning(f"No repos found in project: {project_path}")
            return

        finder_config = FuzzyFinderConfig(
            items=repos,
            prompt_text="🔍 Search repos: ",
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

        # Do nothing if no selection was made (result is None)
        if selected is None:
            logger.info("No repository selected")
            return

        logger.echo(f"Selected: {selected}")

        # Open the selected repository in the configured editor
        selected_path = os.path.join(project_path, selected)
        editor_result = open_editor(app_config.editor, selected_path)
        if isinstance(editor_result, Exception):
            logger.warning(f"Failed to open editor: {editor_result}")
        else:
            logger.info(f"Opened {selected} in {app_config.editor}")

    except Exception as e:
        logger.error(f"Failed to select project repo: {e}")
        ctx.abort()


@repo.command("add")
@click.option("--name", help="Repository name")
@click.option("--description", help="Repository description")
@click.option(
    "--kind", type=click.Choice([k.value for k in ProjectKind]), help="Project kind"
)
@click.option("--ref", help="Reference in the current project for the target project")
@click.option("--path", help="Local project path")
@click.option("--url", help="Repository URL")
@click.option("--sync/--no-sync", default=None, help="Sync setting")
@click.option("--language", help="Programming language")
@click.option("--language-version", help="Language version")
@click.option("--package-manager", help="Package manager")
@click.option(
    "--frameworks",
    multiple=True,
    help="Frameworks used (can be specified multiple times)",
)
@click.option(
    "--prompt",
    is_flag=True,
    help="Use interactive prompts instead of command line parameters",
)
@click.pass_context
def repo_add(
    ctx: click.Context,
    name: Optional[str],
    description: Optional[str],
    kind: Optional[str],
    ref: Optional[str],
    path: Optional[str],
    url: Optional[str],
    sync: Optional[bool],
    language: Optional[str],
    language_version: Optional[str],
    package_manager: Optional[str],
    frameworks: tuple[str, ...],
    prompt: bool,
) -> None:
    """Add a repository to the current project"""
    logger: UnifiedLogger = ctx.obj["logger"]
    project: str = ctx.obj["project"]
    app_config: AppConfig = ctx.obj["config"]
    local_config = ctx.obj["local_config"]
    config_path = ctx.obj["config_path"]

    try:
        # Initialize ProjectManager and MetagitConfigManager
        project_manager = ProjectManager(app_config.workspace.path, logger)
    except Exception as e:
        logger.warning(f"Failed to initialize ProjectManager: {e}")
        ctx.abort()

    try:
        if prompt:
            # Use native ProjectManager prompting functionality
            logger.debug(
                "Using interactive prompts to collect repository information..."
            )
            result = project_manager.add(
                config_path, project, None, metagit_config=local_config
            )
        else:
            # Validate that name is provided when not using prompts
            if not name:
                logger.error(
                    "Repository name is required when not using --prompt option"
                )
                ctx.abort()

            # Create ProjectPath object from parameters
            repo_data = {
                "name": name,
                "description": description,
                "kind": ProjectKind(kind) if kind else None,
                "ref": ref,
                "path": path,
                "url": url,
                "sync": sync,
                "language": language,
                "language_version": language_version,
                "package_manager": package_manager,
                "frameworks": list(frameworks) if frameworks else None,
            }

            # Remove None values
            repo_data = {k: v for k, v in repo_data.items() if v is not None}

            # Create ProjectPath object
            project_path = ProjectPath(**repo_data)

            # Add repository to project
            result = project_manager.add(
                config_path, project, project_path, local_config
            )

        if isinstance(result, Exception):
            raise Exception(f"Failed to add repository to project '{project}'")

        else:
            repo_name = result.name if result.name else "repository"
            logger.info(
                f"Successfully added repository '{repo_name}' to project '{project}'"
            )
            logger.info(
                f"You can now use `metagit repo sync --project {project}` to sync the repository"
            )

    except Exception as e:
        logger.warning(f"Failed to add repository: {e}")


#        ctx.abort()

#!/usr/bin/env python
"""
Project repo subcommand
"""

from typing import Optional

import click

from metagit.core.appconfig import AppConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.project.manager import ProjectManager
from metagit.core.project.models import ProjectKind, ProjectPath
from metagit.core.utils.common import open_editor
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
    """Select project repo to work on"""
    logger = ctx.obj["logger"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    project = ctx.obj["project"]
    app_config: AppConfig = ctx.obj["config"]
    project_manager = ProjectManager(app_config.workspace.path, logger)
    selected_repo = project_manager.select_repo(local_config, project)
    if isinstance(selected_repo, Exception):
        logger.error(f"Failed to select project repo: {selected_repo}")
        ctx.abort()
    if selected_repo is None:
        logger.info("No repo selected")
        ctx.abort()
    logger.info(f"Selected repo: {selected_repo}")
    editor_result = open_editor(app_config.editor, selected_repo)
    if isinstance(editor_result, Exception):
        logger.error(f"Failed to open editor: {editor_result}")
    else:
        logger.info(f"Opened {selected_repo} in {app_config.editor}")


@repo.command("add")
@click.option("--name", "-n", help="Repository name")
@click.option("--description", "-d", help="Repository description")
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

    if project == "local":
        raise click.UsageError("The local project is not supported for this command")

    try:
        # Initialize ProjectManager and MetagitConfigManager
        project_manager = ProjectManager(app_config.workspace.path, logger)
    except Exception as e:
        logger.warning(f"Failed to initialize ProjectManager: {e}")
        ctx.abort()

    try:
        if not name or prompt:
            result = project_manager.add(
                config_path, project, None, metagit_config=local_config
            )
        elif name:
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

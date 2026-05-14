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
    project_manager = ProjectManager(
        app_config.workspace.path,
        logger,
    )
    selected_repo = project_manager.select_repo(
        local_config,
        project,
        show_preview=app_config.workspace.ui_show_preview,
        menu_length=app_config.workspace.ui_menu_length,
        ignore_hidden=app_config.workspace.ui_ignore_hidden,
    )
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


@repo.command("prune")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="List unmanaged directories only; do not prompt or delete.",
)
@click.option(
    "--include-hidden",
    is_flag=True,
    default=False,
    help="Include dot-directories (overrides workspace.ui_ignore_hidden).",
)
@click.pass_context
def repo_prune(
    ctx: click.Context,
    dry_run: bool,
    include_hidden: bool,
) -> None:
    """
    Walk the project sync folder and offer to remove directories not in .metagit.yml.

    Only considers immediate children of the project directory (same layout as sync).
    """
    logger: UnifiedLogger = ctx.obj["logger"]
    project: str = ctx.obj["project"]
    app_config: AppConfig = ctx.obj["config"]
    local_config = ctx.obj["local_config"]

    if project == "local":
        raise click.UsageError("The local project is not supported for this command")

    if not local_config.workspace:
        logger.error("No workspace configuration found")
        ctx.abort()

    try:
        project_manager = ProjectManager(app_config.workspace.path, logger)
    except Exception as exc:
        logger.warning(f"Failed to initialize ProjectManager: {exc}")
        ctx.abort()

    ignore_hidden = (
        False if include_hidden else bool(app_config.workspace.ui_ignore_hidden)
    )
    candidates = project_manager.list_unmanaged_sync_directories(
        local_config,
        project,
        ignore_hidden=ignore_hidden,
    )
    if not candidates:
        logger.info("No unmanaged sync directories found.")
        return

    logger.info(
        f"Found {len(candidates)} unmanaged entr{'y' if len(candidates) == 1 else 'ies'} "
        f"under project {project!r}:"
    )
    for path in candidates:
        click.echo(f"  - {path}")

    if dry_run:
        logger.info("Dry run: no changes made.")
        return

    removed = 0
    for path in candidates:
        rel = path.name
        if not click.confirm(
            f"Remove unmanaged path {rel!r} at {path}?", default=False
        ):
            continue
        try:
            project_manager.remove_sync_directory(path)
            removed += 1
            logger.success(f"Removed {path}")
        except OSError as exc:
            logger.error(f"Failed to remove {path}: {exc}")

    logger.info(f"Prune finished ({removed} removed).")

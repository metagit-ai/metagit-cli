#!/usr/bin/env python
"""
Project repo subcommand
"""

from pathlib import Path
from typing import Optional

import click

from metagit.cli.json_output import (
    emit_json,
    exit_on_catalog_mutation,
    exit_on_layout_mutation,
)
from metagit.core.appconfig import AppConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.project.manager import project_manager_from_app
from metagit.core.project.models import ProjectKind, ProjectPath
from metagit.core.utils.common import open_editor
from metagit.core.workspace.catalog_models import CatalogMutationResult
from metagit.core.workspace.catalog_service import WorkspaceCatalogService
from metagit.core.workspace.layout_service import WorkspaceLayoutService
from metagit.core.workspace import workspace_dedupe
from metagit.core.workspace.dedupe_resolver import (
    resolve_dedupe_for_layout,
    resolve_effective_dedupe_for_project,
)
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
    project_manager = project_manager_from_app(
        app_config,
        logger,
        metagit_config=local_config,
        project_name=project,
    )
    agent_mode = bool(ctx.obj.get("agent_mode", False))
    selected_repo = project_manager.select_repo(
        local_config,
        project,
        show_preview=app_config.workspace.ui_show_preview,
        menu_length=app_config.workspace.ui_menu_length,
        ignore_hidden=app_config.workspace.ui_ignore_hidden,
        agent_mode=agent_mode,
    )
    if isinstance(selected_repo, Exception):
        logger.error(f"Failed to select project repo: {selected_repo}")
        ctx.abort()
    if selected_repo is None:
        logger.info("No repo selected")
        ctx.abort()
    logger.info(f"Selected repo: {selected_repo}")
    if not agent_mode:
        editor_result = open_editor(app_config.editor, selected_repo)
        if isinstance(editor_result, Exception):
            logger.error(f"Failed to open editor: {editor_result}")
        else:
            logger.info(f"Opened {selected_repo} in {app_config.editor}")


@repo.command("list")
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Print JSON for agents"
)
@click.pass_context
def repo_list(ctx: click.Context, as_json: bool) -> None:
    """List repositories for the current workspace project."""
    project: str = ctx.obj["project"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    app_config: AppConfig = ctx.obj["config"]
    if project == "local":
        raise click.UsageError("The local project is not supported for this command")
    workspace_root = str(Path(app_config.workspace.path).expanduser().resolve())
    result = WorkspaceCatalogService().list_repos(
        local_config,
        workspace_root,
        project_name=project,
    )
    if as_json:
        emit_json(result)
        return
    for row in (result.data or {}).get("repos", []):
        repo_row = row.get("repo", {})
        click.echo(
            f"{repo_row.get('name')} path={row.get('configured_path')} "
            f"status={row.get('status') or 'unknown'}"
        )


@repo.command("remove")
@click.option("--name", "-n", required=True, help="Repository name")
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Print JSON for agents"
)
@click.pass_context
def repo_remove(ctx: click.Context, name: str, as_json: bool) -> None:
    """Remove a repository from the manifest (does not delete files)."""
    project: str = ctx.obj["project"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    config_path: str = ctx.obj["config_path"]
    if project == "local":
        raise click.UsageError("The local project is not supported for this command")
    result = WorkspaceCatalogService().remove_repo(
        local_config,
        config_path,
        project_name=project,
        repo_name=name,
    )
    exit_on_catalog_mutation(result, as_json=as_json)


@repo.command("rename")
@click.option(
    "--name", "-n", "from_name", required=True, help="Current repository name"
)
@click.argument("to_name")
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--manifest-only", is_flag=True, default=False)
@click.option("--force", is_flag=True, default=False)
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Print JSON for agents"
)
@click.pass_context
def repo_rename(
    ctx: click.Context,
    from_name: str,
    to_name: str,
    dry_run: bool,
    manifest_only: bool,
    force: bool,
    as_json: bool,
) -> None:
    """Rename a repository in the current project."""
    project: str = ctx.obj["project"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    config_path: str = ctx.obj["config_path"]
    app_config: AppConfig = ctx.obj["config"]
    workspace_root = str(Path(app_config.workspace.path).expanduser().resolve())
    dedupe = resolve_dedupe_for_layout(
        app_config.workspace.dedupe,
        local_config,
        project,
    )
    result = WorkspaceLayoutService().rename_repo(
        local_config,
        config_path,
        workspace_root,
        project_name=project,
        from_name=from_name,
        to_name=to_name,
        dedupe=dedupe,
        dry_run=dry_run,
        move_disk=not manifest_only,
        force=force,
    )
    exit_on_layout_mutation(result, as_json=as_json)


@repo.command("move")
@click.option("--name", "-n", "repo_name", required=True, help="Repository name")
@click.option("--to-project", required=True, help="Target workspace project")
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--manifest-only", is_flag=True, default=False)
@click.option("--force", is_flag=True, default=False)
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Print JSON for agents"
)
@click.pass_context
def repo_move(
    ctx: click.Context,
    repo_name: str,
    to_project: str,
    dry_run: bool,
    manifest_only: bool,
    force: bool,
    as_json: bool,
) -> None:
    """Move a repository to another workspace project."""
    project: str = ctx.obj["project"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    config_path: str = ctx.obj["config_path"]
    app_config: AppConfig = ctx.obj["config"]
    workspace_root = str(Path(app_config.workspace.path).expanduser().resolve())
    dedupe = resolve_dedupe_for_layout(
        app_config.workspace.dedupe,
        local_config,
        to_project,
    )
    result = WorkspaceLayoutService().move_repo(
        local_config,
        config_path,
        workspace_root,
        repo_name=repo_name,
        from_project=project,
        to_project=to_project,
        dedupe=dedupe,
        dry_run=dry_run,
        move_disk=not manifest_only,
        force=force,
    )
    exit_on_layout_mutation(result, as_json=as_json)


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
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Print JSON for agents"
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
    as_json: bool,
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
        project_manager = project_manager_from_app(
            app_config,
            logger,
            metagit_config=local_config,
            project_name=project,
        )
    except Exception as e:
        logger.warning(f"Failed to initialize ProjectManager: {e}")
        ctx.abort()

    catalog = WorkspaceCatalogService()
    try:
        agent_mode = bool(ctx.obj.get("agent_mode", False))
        if (not name or prompt) and agent_mode:
            raise click.UsageError(
                "Interactive repo add is disabled in agent mode; "
                "pass --name and --path or --url, or use workspace repo add --json"
            )
        if not name or prompt:
            result = project_manager.add(
                config_path,
                project,
                None,
                metagit_config=local_config,
                agent_mode=agent_mode,
            )
            if isinstance(result, Exception):
                raise result
            if as_json:
                emit_json(
                    CatalogMutationResult(
                        ok=True,
                        entity="repo",
                        operation="add",
                        project_name=project,
                        repo_name=result.name,
                        config_path=str(Path(config_path).resolve()),
                    )
                )
                return
        else:
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
            repo_data = {k: v for k, v in repo_data.items() if v is not None}
            project_path = ProjectPath(**repo_data)
            if as_json:
                mutation = catalog.add_repo(
                    local_config,
                    config_path,
                    project_name=project,
                    repo=project_path,
                )
                exit_on_catalog_mutation(mutation, as_json=True)
                return
            result = project_manager.add(
                config_path,
                project,
                project_path,
                local_config,
                agent_mode=agent_mode,
            )

        if isinstance(result, Exception):
            raise result

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
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Remove all listed unmanaged paths without prompting (no effect with --dry-run).",
)
@click.pass_context
def repo_prune(
    ctx: click.Context,
    dry_run: bool,
    include_hidden: bool,
    force: bool,
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
        project_manager = project_manager_from_app(
            app_config,
            logger,
            metagit_config=local_config,
            project_name=project,
        )
    except Exception as exc:
        logger.warning(f"Failed to initialize ProjectManager: {exc}")
        ctx.abort()

    workspace_root = Path(app_config.workspace.path).expanduser().resolve()
    project_sync_folder = (workspace_root / project).resolve()
    click.echo("Prune context:")
    click.echo(f"  workspace.path (sync root): {workspace_root}")
    click.echo(f"  project: {project}")
    click.echo(f"  project sync folder: {project_sync_folder}")

    ignore_hidden = (
        False if include_hidden else bool(app_config.workspace.ui_ignore_hidden)
    )
    candidates = project_manager.list_unmanaged_sync_directories(
        local_config,
        project,
        ignore_hidden=ignore_hidden,
    )
    dedupe = resolve_effective_dedupe_for_project(
        app_config.workspace.dedupe,
        local_config,
        project,
    )
    if dedupe is not None:
        references = workspace_dedupe.list_canonical_references(
            local_config,
            workspace_root,
            dedupe,
        )
        orphans = workspace_dedupe.list_orphan_canonical_dirs(
            workspace_root,
            dedupe,
            references,
        )
        if orphans:
            click.echo("Orphan canonical directories (not referenced in .metagit.yml):")
            for orphan in orphans:
                click.echo(f"  - {orphan}")
        else:
            click.echo("No orphan canonical directories under _canonical/.")
    if not candidates:
        click.echo("No unmanaged sync directories found under the project sync folder.")
        return

    click.echo(
        f"Found {len(candidates)} unmanaged entr{'y' if len(candidates) == 1 else 'ies'}:"
    )
    for path in candidates:
        click.echo(f"  - {path}")

    if dry_run:
        click.echo("Dry run: no changes made.")
        return

    if ctx.obj.get("agent_mode") and not force:
        raise click.UsageError(
            "Interactive prune prompts are disabled in agent mode; use --force or --dry-run"
        )

    removed = 0
    for path in candidates:
        rel = path.name
        if not force and not click.confirm(
            f"Remove unmanaged path {rel!r} at {path}?", default=False
        ):
            continue
        try:
            project_manager.remove_sync_directory(path)
            removed += 1
            logger.success(f"Removed {path}")
        except OSError as exc:
            logger.error(f"Failed to remove {path}: {exc}")

    if force:
        click.echo(f"Prune finished (--force): {removed} removed.")
    else:
        click.echo(f"Prune finished: {removed} removed.")

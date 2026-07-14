"""
Project subcommand
"""

import sys
from pathlib import Path
from typing import Optional

import click
import yaml

from metagit.cli.commands.project_repo import execute_repo_select, repo
from metagit.cli.commands.project_source import source
from metagit.cli.json_output import (
    emit_json,
    exit_on_catalog_mutation,
    exit_on_layout_mutation,
)
from metagit.cli.shell_completion import complete_projects, complete_repos
from metagit.core.appconfig import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.project.manager import ProjectManager, project_manager_from_app
from metagit.core.project.source_manifest_sync import SourceManifestSyncService
from metagit.core.utils.logging import UnifiedLogger
from metagit.core.workspace.catalog_service import WorkspaceCatalogService
from metagit.core.workspace.dedupe_resolver import resolve_dedupe_for_layout
from metagit.core.workspace.layout_resolver import (
    active_project_resolution_error,
    resolve_active_project_name,
)
from metagit.core.workspace.layout_service import WorkspaceLayoutService
from metagit.core.workspace.models import WorkspaceProject
from metagit.core.workspace.root_resolver import resolve_session_root


@click.group(name="project", invoke_without_command=True)
@click.option("--config", "-c", default=".metagit.yml", help="Path to the metagit definition file")
@click.option(
    "--project",
    "-p",
    default=None,
    help="Project within workspace to operate on",
    shell_complete=complete_projects,
)
@click.pass_context
def project(ctx: click.Context, config: str, project: str = None) -> None:
    """Project subcommands"""
    logger = ctx.obj["logger"]
    # If no subcommand is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return
    app_config: AppConfig = ctx.obj["config"]
    ctx.obj["config_path"] = config
    ctx.obj["explicit_project"] = project
    try:
        config_manager: MetagitConfigManager = MetagitConfigManager(config)
        local_config: MetagitConfig = config_manager.load_config()
        ctx.obj["local_config"] = local_config
        if isinstance(local_config, Exception):
            raise local_config
    except Exception as e:
        logger.error(f"Failed to load metagit definition file: {e}")
        sys.exit(1)
    ctx.obj["project"] = resolve_active_project_name(
        local_config,
        explicit=project,
        default_project=app_config.workspace.default_project,
    )


# Add repo group to project group
project.add_command(repo)
project.add_command(source)


@project.command("list")
@click.option(
    "--all",
    "list_all",
    is_flag=True,
    default=False,
    help="Deprecated alias: catalog listing is now the default without -p/--project",
)
@click.option(
    "--detail",
    "show_detail",
    is_flag=True,
    default=False,
    help="Dump the active/explicit project as YAML (or JSON with --json)",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def project_list(
    ctx: click.Context,
    list_all: bool,
    show_detail: bool,
    as_json: bool,
) -> None:
    """List workspace projects (catalog), or one project with -p/--detail."""
    logger: UnifiedLogger = ctx.obj["logger"]
    project: str = ctx.obj["project"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    config_path: str = ctx.obj["config_path"]
    app_config: AppConfig = ctx.obj["config"]
    explicit_project = ctx.obj.get("explicit_project")
    _ = list_all  # retained for backward-compatible CLI flag

    # Catalog is the default. Detail/YAML dump only when -p is explicit or --detail.
    use_detail = bool(explicit_project) or show_detail
    if not use_detail:
        service = WorkspaceCatalogService()
        workspace_root = str(Path(app_config.workspace.path).expanduser().resolve())
        result = service.list_workspace(
            local_config,
            config_path,
            workspace_root,
            include_index=False,
        )
        if as_json:
            emit_json(result)
            return
        summary = (result.data or {}).get("summary", {})
        click.echo(f"Definition: {summary.get('definition_path', config_path)}")
        click.echo(f"Workspace root: {summary.get('workspace_root', workspace_root)}")
        click.echo(f"Projects: {summary.get('project_count', 0)} | Repos: {summary.get('repo_count', 0)}")
        for entry in (result.data or {}).get("projects", []):
            click.echo(f"  - {entry.get('name')} ({entry.get('repo_count', 0)} repos)")
        return

    try:
        target = explicit_project or project
        if not target:
            logger.error(active_project_resolution_error(local_config))
            ctx.abort()

        # Handle special "local" project case
        if target == "local":
            # Check if there's an existing project named "local" in workspace
            if local_config.workspace:
                workspace_project: WorkspaceProject = next(
                    (p for p in local_config.workspace.projects if p.name == target),
                    None,
                )
                if workspace_project:
                    # Use existing "local" project
                    project_dict = workspace_project.model_dump(exclude_none=True)
                else:
                    # Use computed local_workspace_project
                    workspace_project = local_config.local_workspace_project
                    project_dict = workspace_project.model_dump(exclude_none=True)
            else:
                # No workspace config, use computed local_workspace_project
                workspace_project = local_config.local_workspace_project
                project_dict = workspace_project.model_dump(exclude_none=True)
        else:
            # Handle regular project names
            if not local_config.workspace:
                logger.error("No workspace configuration found")
                ctx.abort()

            workspace_project: WorkspaceProject = next(
                (p for p in local_config.workspace.projects if p.name == target), None
            )

            if not workspace_project:
                logger.error(f"Project '{target}' not found in workspace configuration")
                ctx.abort()

            project_dict = workspace_project.model_dump(exclude_none=True)

        if as_json:
            emit_json(project_dict)
            return
        yaml_output = yaml.dump(project_dict, default_flow_style=False, sort_keys=False)
        logger.echo(yaml_output)

    except click.Abort:
        raise
    except Exception as e:
        logger.error(f"Failed to list project: {e}")
        ctx.abort()


@project.command("add")
@click.argument("name")
@click.option("--description", default=None)
@click.option("--agent-instructions", default=None)
@click.option(
    "--ensure",
    is_flag=True,
    help="Succeed without changes when the project already exists with matching fields",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def project_add(
    ctx: click.Context,
    name: str,
    description: str | None,
    agent_instructions: str | None,
    ensure: bool,
    as_json: bool,
) -> None:
    """Add a workspace project to the manifest."""
    local_config: MetagitConfig = ctx.obj["local_config"]
    config_path: str = ctx.obj["config_path"]
    ensure_mode = ensure or bool(ctx.obj.get("agent_mode", False))
    result = WorkspaceCatalogService().add_project(
        local_config,
        config_path,
        name=name,
        description=description,
        agent_instructions=agent_instructions,
        ensure=ensure_mode,
    )
    exit_on_catalog_mutation(result, as_json=as_json)


@project.command("remove")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def project_remove(ctx: click.Context, name: str, as_json: bool) -> None:
    """Remove a workspace project from the manifest."""
    local_config: MetagitConfig = ctx.obj["local_config"]
    config_path: str = ctx.obj["config_path"]
    result = WorkspaceCatalogService().remove_project(
        local_config,
        config_path,
        name=name,
    )
    exit_on_catalog_mutation(result, as_json=as_json)


@project.command("rename")
@click.argument("from_name")
@click.argument("to_name")
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--manifest-only", is_flag=True, default=False)
@click.option("--force", is_flag=True, default=False)
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def project_rename(
    ctx: click.Context,
    from_name: str,
    to_name: str,
    dry_run: bool,
    manifest_only: bool,
    force: bool,
    as_json: bool,
) -> None:
    """Rename a workspace project (alias for workspace project rename)."""
    local_config: MetagitConfig = ctx.obj["local_config"]
    config_path: str = ctx.obj["config_path"]
    app_config: AppConfig = ctx.obj["config"]
    workspace_root = str(Path(app_config.workspace.path).expanduser().resolve())
    dedupe = resolve_dedupe_for_layout(
        app_config.workspace.dedupe,
        local_config,
        from_name,
    )
    result = WorkspaceLayoutService().rename_project(
        local_config,
        config_path,
        workspace_root,
        from_name=from_name,
        to_name=to_name,
        dedupe=dedupe,
        dry_run=dry_run,
        move_disk=not manifest_only,
        force=force,
    )
    exit_on_layout_mutation(result, as_json=as_json)


@project.command("select")
@click.option(
    "--repo",
    "repo_name",
    default=None,
    help="Open this repository in the default editor without the picker TUI",
    shell_complete=complete_repos,
)
@click.pass_context
def project_select(ctx: click.Context, repo_name: Optional[str]) -> None:
    """Shortcut: Uses 'project repo select' to select workspace project repo to work on"""
    execute_repo_select(ctx, repo_name=repo_name)


@project.command("sync")
@click.option(
    "--hydrate",
    is_flag=True,
    default=False,
    help="After sync, replace symlink mounts with full directory copies",
)
@click.option(
    "--refresh-sources",
    is_flag=True,
    default=False,
    help="Apply workspace.projects[].sources[] before git sync",
)
@click.pass_context
def project_sync(ctx: click.Context, hydrate: bool, refresh_sources: bool) -> None:
    """Sync project within workspace"""
    logger = ctx.obj["logger"]
    app_config: AppConfig = ctx.obj["config"]
    project: str | None = ctx.obj["project"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    if not project:
        logger.error(active_project_resolution_error(local_config))
        ctx.abort()
    project_manager: ProjectManager = project_manager_from_app(
        app_config,
        logger,
        metagit_config=local_config,
        project_name=project,
    )

    try:
        # Handle special "local" project case
        if project == "local":
            # Check if there's an existing project named "local" in workspace
            if local_config.workspace:
                workspace_project: WorkspaceProject = next(
                    (p for p in local_config.workspace.projects if p.name == project),
                    None,
                )
                if workspace_project:
                    # Use existing "local" project
                    pass
                else:
                    # Use computed local_workspace_project
                    workspace_project = local_config.local_workspace_project
            else:
                # No workspace config, use computed local_workspace_project
                workspace_project = local_config.local_workspace_project
        else:
            # Handle regular project names
            if not local_config.workspace:
                logger.error("No workspace configuration found")
                ctx.abort()

            workspace_project: WorkspaceProject = next(
                (p for p in local_config.workspace.projects if p.name == project), None
            )

            if not workspace_project:
                logger.error(f"Project '{project}' not found in workspace configuration")
                ctx.abort()

        if refresh_sources and project != "local":
            config_path = ctx.obj["config_path"]
            manifest_result = SourceManifestSyncService().sync_project(
                app_config=app_config,
                logger=logger,
                config=local_config,
                config_path=config_path,
                project_name=project,
                apply=True,
                sync_clones=False,
                session_root=resolve_session_root(config_path),
            )
            if not manifest_result.ok:
                for error in manifest_result.errors:
                    logger.error(error.message)
                ctx.abort()
            workspace_project = next(
                (p for p in local_config.workspace.projects if p.name == project),
                workspace_project,
            )

        sync_result: bool = project_manager.sync(workspace_project, hydrate=hydrate)
        if sync_result:
            logger.success(f"Project {project} synced successfully")
            exit(0)
        else:
            logger.error(f"Failed to sync project {project}")
            ctx.abort()

    except Exception as e:
        logger.error(f"Failed to sync project: {e}")
        ctx.abort()

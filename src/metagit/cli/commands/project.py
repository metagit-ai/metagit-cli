"""
Project subcommand
"""

import sys
from pathlib import Path

import click
import yaml

from metagit.cli.commands.project_repo import repo, repo_select
from metagit.cli.json_output import (
    emit_json,
    exit_on_catalog_mutation,
    exit_on_layout_mutation,
)
from metagit.cli.commands.project_source import source
from metagit.core.appconfig import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.project.manager import ProjectManager, project_manager_from_app
from metagit.core.utils.click import call_click_command_with_ctx
from metagit.core.utils.logging import UnifiedLogger
from metagit.core.workspace.catalog_service import WorkspaceCatalogService
from metagit.core.workspace.dedupe_resolver import resolve_dedupe_for_layout
from metagit.core.workspace.layout_service import WorkspaceLayoutService
from metagit.core.workspace.models import WorkspaceProject


@click.group(name="project", invoke_without_command=True)
@click.option(
    "--config", "-c", default=".metagit.yml", help="Path to the metagit definition file"
)
@click.option(
    "--project",
    "-p",
    default=None,
    help="Project within workspace to operate on",
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
    if not project:
        project: str = app_config.workspace.default_project
    ctx.obj["project"] = project
    ctx.obj["config_path"] = config
    try:
        config_manager: MetagitConfigManager = MetagitConfigManager(config)
        local_config: MetagitConfig = config_manager.load_config()
        ctx.obj["local_config"] = local_config
        if isinstance(local_config, Exception):
            raise local_config
    except Exception as e:
        logger.error(f"Failed to load metagit definition file: {e}")
        sys.exit(1)


# Add repo group to project group
project.add_command(repo)
project.add_command(source)


@project.command("list")
@click.option(
    "--all",
    "list_all",
    is_flag=True,
    default=False,
    help="List all workspace projects (catalog view) instead of one project YAML",
)
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Print JSON for agents"
)
@click.pass_context
def project_list(ctx: click.Context, list_all: bool, as_json: bool) -> None:
    """List project configuration (YAML, JSON, or all projects)."""
    logger: UnifiedLogger = ctx.obj["logger"]
    project: str = ctx.obj["project"]
    local_config: MetagitConfig = ctx.obj["local_config"]

    if list_all:
        service = WorkspaceCatalogService()
        if as_json:
            emit_json(service.list_projects(local_config))
            return
        result = service.list_projects(local_config)
        for entry in (result.data or {}).get("projects", []):
            logger.echo(f"{entry.get('name')} ({entry.get('repo_count', 0)} repos)")
        return

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
                (p for p in local_config.workspace.projects if p.name == project), None
            )

            if not workspace_project:
                logger.error(
                    f"Project '{project}' not found in workspace configuration"
                )
                ctx.abort()

            project_dict = workspace_project.model_dump(exclude_none=True)

        if as_json:
            emit_json(project_dict)
            return
        yaml_output = yaml.dump(project_dict, default_flow_style=False, sort_keys=False)
        logger.echo(yaml_output)

    except Exception as e:
        logger.error(f"Failed to list project: {e}")
        ctx.abort()


@project.command("add")
@click.argument("name")
@click.option("--description", default=None)
@click.option("--agent-instructions", default=None)
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Print JSON for agents"
)
@click.pass_context
def project_add(
    ctx: click.Context,
    name: str,
    description: str | None,
    agent_instructions: str | None,
    as_json: bool,
) -> None:
    """Add a workspace project to the manifest."""
    local_config: MetagitConfig = ctx.obj["local_config"]
    config_path: str = ctx.obj["config_path"]
    result = WorkspaceCatalogService().add_project(
        local_config,
        config_path,
        name=name,
        description=description,
        agent_instructions=agent_instructions,
    )
    exit_on_catalog_mutation(result, as_json=as_json)


@project.command("remove")
@click.argument("name")
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Print JSON for agents"
)
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
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Print JSON for agents"
)
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
@click.pass_context
def project_select(ctx: click.Context) -> None:
    """Shortcut: Uses 'project repo select' to select workspace project repo to work on"""
    # Call the repo_select function
    call_click_command_with_ctx(repo_select, ctx)


@project.command("sync")
@click.pass_context
def project_sync(ctx: click.Context) -> None:
    """Sync project within workspace"""
    logger = ctx.obj["logger"]
    app_config: AppConfig = ctx.obj["config"]
    project: str = ctx.obj["project"]
    local_config: MetagitConfig = ctx.obj["local_config"]
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
                logger.error(
                    f"Project '{project}' not found in workspace configuration"
                )
                ctx.abort()

        sync_result: bool = project_manager.sync(workspace_project)
        if sync_result:
            logger.success(f"Project {project} synced successfully")
            exit(0)
        else:
            logger.error(f"Failed to sync project {project}")
            ctx.abort()

    except Exception as e:
        logger.error(f"Failed to sync project: {e}")
        ctx.abort()

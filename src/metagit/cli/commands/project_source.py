#!/usr/bin/env python
"""
Project source sync subcommand.
"""

from typing import Optional

import click

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.project.source_models import SourceSpec, SourceSyncMode
from metagit.core.project.source_sync import SourceSyncService
from metagit.core.utils.logging import UnifiedLogger
from metagit.core.workspace.models import WorkspaceProject


@click.group(name="source")
@click.pass_context
def source(ctx: click.Context) -> None:
    """Source-backed project sync operations."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@source.command("sync")
@click.option(
    "--provider",
    type=click.Choice(["github", "gitlab"]),
    required=True,
    help="Source provider",
)
@click.option("--org", help="GitHub organization to discover repositories from")
@click.option("--user", help="GitHub user to discover repositories from")
@click.option("--group", help="GitLab group path to discover repositories from")
@click.option(
    "--mode",
    type=click.Choice([mode.value for mode in SourceSyncMode]),
    default=SourceSyncMode.DISCOVER.value,
    show_default=True,
    help="Sync mode",
)
@click.option(
    "--recursive/--no-recursive",
    default=True,
    show_default=True,
    help="Recursive traversal when supported by provider",
)
@click.option(
    "--include-archived/--no-include-archived",
    default=False,
    show_default=True,
    help="Include archived repositories",
)
@click.option(
    "--include-forks/--no-include-forks",
    default=False,
    show_default=True,
    help="Include forks",
)
@click.option(
    "--path-prefix", default=None, help="Optional namespace/repo prefix filter"
)
@click.option(
    "--apply/--no-apply",
    default=False,
    show_default=True,
    help="Apply computed changes to .metagit.yml",
)
@click.option(
    "--yes",
    is_flag=True,
    default=False,
    help="Confirm destructive reconcile removals",
)
@click.pass_context
def source_sync(
    ctx: click.Context,
    provider: str,
    org: Optional[str],
    user: Optional[str],
    group: Optional[str],
    mode: str,
    recursive: bool,
    include_archived: bool,
    include_forks: bool,
    path_prefix: Optional[str],
    apply: bool,
    yes: bool,
) -> None:
    """Discover and sync repositories from provider sources."""
    logger: UnifiedLogger = ctx.obj["logger"]
    app_config: AppConfig = ctx.obj["config"]
    project_name: str = ctx.obj["project"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    config_path: str = ctx.obj["config_path"]

    try:
        spec = SourceSpec(
            provider=provider,
            org=org,
            user=user,
            group=group,
            recursive=recursive,
            include_archived=include_archived,
            include_forks=include_forks,
            path_prefix=path_prefix,
        )
    except Exception as exc:
        raise click.UsageError(str(exc)) from exc

    if not local_config.workspace:
        raise click.UsageError("No workspace configuration found in .metagit.yml")

    workspace_project: Optional[WorkspaceProject] = next(
        (item for item in local_config.workspace.projects if item.name == project_name),
        None,
    )
    if not workspace_project:
        raise click.UsageError(
            f"Project '{project_name}' not found in workspace configuration"
        )

    service = SourceSyncService(app_config, logger)
    discovered_result = service.discover(spec)
    if isinstance(discovered_result, Exception):
        logger.error(f"Source discovery failed: {discovered_result}")
        ctx.abort()
    discovered = discovered_result

    sync_mode = SourceSyncMode(mode)
    plan = service.plan(spec, workspace_project, discovered, sync_mode)

    logger.info(f"Discovered repositories: {plan.discovered_count}")
    logger.info(f"Planned add: {len(plan.to_add)}")
    logger.info(f"Planned update: {len(plan.to_update)}")
    logger.info(f"Planned remove: {len(plan.to_remove)}")
    logger.info(f"Unchanged: {plan.unchanged}")

    if len(plan.to_add) > 0:
        logger.info(
            "Add candidates: " + ", ".join(repo.name for repo in plan.to_add[:20])
        )
    if len(plan.to_update) > 0:
        logger.info(
            "Update candidates: " + ", ".join(repo.name for repo in plan.to_update[:20])
        )
    if len(plan.to_remove) > 0:
        logger.warning(
            "Remove candidates: " + ", ".join(repo.name for repo in plan.to_remove[:20])
        )

    if not apply or sync_mode == SourceSyncMode.DISCOVER:
        logger.info("Dry-run complete (no config changes applied).")
        return

    if sync_mode == SourceSyncMode.RECONCILE and len(plan.to_remove) > 0 and not yes:
        raise click.UsageError(
            "Reconcile mode has removals. Re-run with --yes to confirm destructive changes."
        )

    updated_project = service.apply_plan(workspace_project, plan, sync_mode)
    for index, item in enumerate(local_config.workspace.projects):
        if item.name == updated_project.name:
            local_config.workspace.projects[index] = updated_project
            break

    config_manager = MetagitConfigManager(config_path=config_path)
    save_result = config_manager.save_config(local_config, config_path)
    if isinstance(save_result, Exception):
        logger.error(f"Failed to save updated config: {save_result}")
        ctx.abort()

    logger.success("Source sync applied successfully.")

#!/usr/bin/env python
"""
Project source sync subcommand.
"""

import json
from typing import Optional

import click

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.project.source_models import (
    SourceSpec,
    SourceSyncError,
    SourceSyncMode,
    SourceSyncResult,
)
from metagit.core.project.source_sync import SourceSyncService
from metagit.core.utils.logging import UnifiedLogger
from metagit.core.workspace.models import WorkspaceProject


def _emit_json(result: SourceSyncResult) -> None:
    click.echo(json.dumps(result.model_dump(mode="json"), indent=2))


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
    "--include-pattern",
    "include_patterns",
    multiple=True,
    help="fnmatch allowlist on provider full_name (repeatable)",
)
@click.option(
    "--ignore",
    "ignore_patterns",
    multiple=True,
    help="fnmatch denylist on provider full_name (repeatable)",
)
@click.option(
    "--name-strategy",
    type=click.Choice(["short", "namespaced"]),
    default="namespaced",
    show_default=True,
    help="Manifest repo naming strategy",
)
@click.option(
    "--ensure",
    is_flag=True,
    default=False,
    help="Skip metadata updates when repo URL already exists",
)
@click.option(
    "--refresh-metadata",
    is_flag=True,
    default=False,
    help="With --ensure, still refresh description and tags",
)
@click.option(
    "--no-enrich-topics",
    is_flag=True,
    default=False,
    help="Do not merge provider topics into repo tags",
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
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print JSON result for agents",
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
    include_patterns: tuple[str, ...],
    ignore_patterns: tuple[str, ...],
    name_strategy: str,
    ensure: bool,
    refresh_metadata: bool,
    no_enrich_topics: bool,
    apply: bool,
    yes: bool,
    as_json: bool,
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
            include_patterns=list(include_patterns),
            ignore_patterns=list(ignore_patterns),
            name_strategy=name_strategy,
            ensure=ensure,
            refresh_metadata=refresh_metadata,
            enrich_topics=not no_enrich_topics,
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
        result = SourceSyncResult(
            ok=False,
            spec=spec.model_dump(mode="json"),
            errors=[
                SourceSyncError(
                    kind="discovery_failed",
                    message=str(discovered_result),
                )
            ],
        )
        if as_json:
            _emit_json(result)
        else:
            logger.error(f"Source discovery failed: {discovered_result}")
        ctx.abort()

    discovered = discovered_result
    sync_mode = SourceSyncMode(mode)
    plan = service.plan(spec, workspace_project, discovered, sync_mode)
    result = SourceSyncResult(
        ok=True,
        applied=False,
        spec=spec.model_dump(mode="json"),
        plan=plan,
    )

    if not as_json:
        logger.info(f"Discovered repositories: {plan.discovered_count}")
        logger.info(f"Filtered repositories: {plan.filtered_count}")
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
                "Update candidates: "
                + ", ".join(repo.name for repo in plan.to_update[:20])
            )
        if len(plan.to_remove) > 0:
            logger.warning(
                "Remove candidates: "
                + ", ".join(repo.name for repo in plan.to_remove[:20])
            )

    if not apply or sync_mode == SourceSyncMode.DISCOVER:
        if not as_json:
            logger.info("Dry-run complete (no config changes applied).")
        else:
            _emit_json(result)
        return

    if sync_mode == SourceSyncMode.RECONCILE and len(plan.to_remove) > 0 and not yes:
        result.ok = False
        result.errors.append(
            SourceSyncError(
                kind="reconcile_confirmation_required",
                message="Reconcile mode has removals. Re-run with --yes to confirm.",
            )
        )
        if as_json:
            _emit_json(result)
        else:
            raise click.UsageError(result.errors[0].message)
        ctx.abort()

    updated_project = service.apply_plan(workspace_project, plan, sync_mode)
    for index, item in enumerate(local_config.workspace.projects):
        if item.name == updated_project.name:
            local_config.workspace.projects[index] = updated_project
            break

    config_manager = MetagitConfigManager(config_path=config_path)
    save_result = config_manager.save_config(local_config, config_path)
    if isinstance(save_result, Exception):
        result.ok = False
        result.errors.append(
            SourceSyncError(kind="save_failed", message=str(save_result))
        )
        if as_json:
            _emit_json(result)
        else:
            logger.error(f"Failed to save updated config: {save_result}")
        ctx.abort()

    result.applied = True
    if as_json:
        _emit_json(result)
    else:
        logger.success("Source sync applied successfully.")

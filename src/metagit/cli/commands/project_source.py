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
from metagit.core.project.source_manifest_sync import (
    SourceManifestSyncService,
    upsert_project_source,
)
from metagit.core.project.source_models import (
    ProjectSource,
    SourceSpec,
    SourceSyncMode,
    SourceSyncResult,
)
from metagit.core.project.source_sync_runner import (
    SourceSyncRunRequest,
    run_source_sync,
)
from metagit.core.utils.logging import UnifiedLogger
from metagit.core.workspace.root_resolver import resolve_session_root


def emit_source_sync_json(result: SourceSyncResult) -> None:
    """Print a source sync JSON envelope to stdout."""
    click.echo(json.dumps(result.model_dump(mode="json"), indent=2))


def build_source_spec_from_cli(
    *,
    provider: str,
    org: Optional[str],
    user: Optional[str],
    group: Optional[str],
    recursive: bool,
    include_archived: bool,
    include_forks: bool,
    path_prefix: Optional[str],
    include_patterns: tuple[str, ...],
    ignore_patterns: tuple[str, ...],
    name_strategy: str,
    ensure: bool,
    refresh_metadata: bool,
    enrich_topics: bool,
) -> SourceSpec:
    """Build ``SourceSpec`` from CLI flag values."""
    return SourceSpec(
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
        enrich_topics=enrich_topics,
    )


def log_source_sync_plan(logger: UnifiedLogger, result: SourceSyncResult) -> None:
    """Emit human-readable plan summary to the logger."""
    if result.plan is None:
        return
    plan = result.plan
    logger.info(f"Discovered repositories: {plan.discovered_count}")
    logger.info(f"Filtered repositories: {plan.filtered_count}")
    logger.info(f"Planned add: {len(plan.to_add)}")
    logger.info(f"Planned update: {len(plan.to_update)}")
    logger.info(f"Planned remove: {len(plan.to_remove)}")
    logger.info(f"Unchanged: {plan.unchanged}")
    if plan.to_add:
        logger.info("Add candidates: " + ", ".join(repo.name for repo in plan.to_add[:20]))
    if plan.to_update:
        logger.info("Update candidates: " + ", ".join(repo.name for repo in plan.to_update[:20]))
    if plan.to_remove:
        logger.warning("Remove candidates: " + ", ".join(repo.name for repo in plan.to_remove[:20]))


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
    required=False,
    help="Source provider (not used with --from-manifest)",
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
@click.option("--path-prefix", default=None, help="Optional namespace/repo prefix filter")
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
    "--sync/--no-sync",
    default=False,
    show_default=True,
    help="Run project git sync after a successful manifest apply",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print JSON result for agents",
)
@click.option(
    "--from-manifest",
    is_flag=True,
    default=False,
    help="Sync using workspace.projects[].sources[] definitions",
)
@click.option("--source-id", default=None, help="Limit manifest sync to one source id")
@click.option(
    "--write-source",
    is_flag=True,
    default=False,
    help="Persist current CLI flags as a sources[] entry (requires --source-id)",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Apply reconcile removals without approval (manifest mode)",
)
@click.pass_context
def source_sync(
    ctx: click.Context,
    provider: Optional[str],
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
    sync: bool,
    as_json: bool,
    from_manifest: bool,
    source_id: Optional[str],
    write_source: bool,
    force: bool,
) -> None:
    """Discover and sync repositories from provider sources."""
    logger: UnifiedLogger = ctx.obj["logger"]
    app_config: AppConfig = ctx.obj["config"]
    project_name: str = ctx.obj["project"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    config_path: str = ctx.obj["config_path"]

    if not local_config.workspace:
        raise click.UsageError("No workspace configuration found in .metagit.yml")

    if from_manifest:
        session_root = resolve_session_root(config_path)
        result = SourceManifestSyncService().sync_project(
            app_config=app_config,
            logger=logger,
            config=local_config,
            config_path=config_path,
            project_name=project_name,
            source_id=source_id,
            apply=apply,
            force=force,
            sync_clones=sync and apply,
            session_root=session_root,
        )
    else:
        if not provider:
            raise click.UsageError("--provider is required unless --from-manifest is set")
        try:
            spec = build_source_spec_from_cli(
                provider=provider,
                org=org,
                user=user,
                group=group,
                recursive=recursive,
                include_archived=include_archived,
                include_forks=include_forks,
                path_prefix=path_prefix,
                include_patterns=include_patterns,
                ignore_patterns=ignore_patterns,
                name_strategy=name_strategy,
                ensure=ensure,
                refresh_metadata=refresh_metadata,
                enrich_topics=not no_enrich_topics,
            )
        except Exception as exc:
            raise click.UsageError(str(exc)) from exc

        if write_source:
            if not source_id:
                raise click.UsageError("--write-source requires --source-id")
            project = next(
                (item for item in local_config.workspace.projects if item.name == project_name),
                None,
            )
            if project is None:
                raise click.UsageError(f"Project '{project_name}' not found")
            manifest_source = ProjectSource(
                id=source_id,
                provider=spec.provider,
                org=spec.org,
                user=spec.user,
                group=spec.group,
                mode=SourceSyncMode(mode),
                recursive=spec.recursive,
                ensure=spec.ensure,
                refresh_metadata=spec.refresh_metadata,
                enrich_topics=spec.enrich_topics,
                include_archived=spec.include_archived,
                include_forks=spec.include_forks,
                path_prefix=spec.path_prefix,
                include_patterns=list(spec.include_patterns),
                ignore_patterns=list(spec.ignore_patterns),
                name_strategy=spec.name_strategy,
            )
            updated = upsert_project_source(project, manifest_source)
            for index, item in enumerate(local_config.workspace.projects):
                if item.name == project_name:
                    local_config.workspace.projects[index] = updated
                    break
            save_result = MetagitConfigManager(config_path=config_path).save_config(local_config, config_path)
            if isinstance(save_result, Exception):
                raise click.UsageError(str(save_result)) from save_result

        result = run_source_sync(
            app_config=app_config,
            logger=logger,
            config=local_config,
            config_path=config_path,
            request=SourceSyncRunRequest(
                spec=spec,
                mode=SourceSyncMode(mode),
                project_name=project_name,
                apply=apply,
                confirm_reconcile=yes,
                sync_clones=sync and apply,
            ),
        )

    if not as_json:
        if result.ok and result.plan is not None:
            log_source_sync_plan(logger, result)
        if not apply or SourceSyncMode(mode) == SourceSyncMode.DISCOVER:
            logger.info("Dry-run complete (no config changes applied).")
        elif result.applied:
            logger.success("Source sync applied successfully.")
        for error in result.errors:
            if error.kind == "reconcile_confirmation_required":
                raise click.UsageError(error.message)
            logger.error(error.message)

    if as_json:
        emit_source_sync_json(result)

    if not result.ok:
        ctx.abort()

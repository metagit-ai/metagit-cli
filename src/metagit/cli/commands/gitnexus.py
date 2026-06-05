#!/usr/bin/env python
"""GitNexus integration commands for Metagit workspaces."""

from __future__ import annotations

import json
from pathlib import Path

import click

from metagit.cli.json_output import emit_json
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.gitnexus.group_sync import GitNexusGroupSyncService


@click.group(name="gitnexus")
def gitnexus() -> None:
    """GitNexus workspace integration (groups, cross-index analysis)."""


@gitnexus.group("group")
def gitnexus_group() -> None:
    """Manage GitNexus repository groups."""


@gitnexus_group.command("sync")
@click.option(
    "--workspace-root",
    default=None,
    help="Workspace sync root (default: appconfig workspace.path)",
)
@click.option(
    "--group-name",
    default=None,
    help="GitNexus group name (default: slug of manifest name)",
)
@click.option(
    "--no-create",
    is_flag=True,
    default=False,
    help="Fail when the group does not exist instead of creating it",
)
@click.option(
    "--prune",
    is_flag=True,
    default=False,
    help="Remove group members no longer present in workspace.projects",
)
@click.option(
    "--no-contract-sync",
    is_flag=True,
    default=False,
    help="Update group membership only; skip gitnexus group sync",
)
@click.option("--allow-stale", is_flag=True, default=False, help="Pass --allow-stale")
@click.option(
    "--skip-embeddings",
    is_flag=True,
    default=False,
    help="Pass --skip-embeddings to contract sync",
)
@click.option(
    "--exact-only",
    is_flag=True,
    default=False,
    help="Pass --exact-only to contract sync",
)
@click.option("--verbose", is_flag=True, default=False, help="Verbose contract sync")
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Print JSON result"
)
@click.pass_context
def gitnexus_group_sync(
    ctx: click.Context,
    workspace_root: str | None,
    group_name: str | None,
    no_create: bool,
    prune: bool,
    no_contract_sync: bool,
    allow_stale: bool,
    skip_embeddings: bool,
    exact_only: bool,
    verbose: bool,
    as_json: bool,
) -> None:
    """
    Sync workspace.projects repos into a GitNexus group and run contract linking.

    Creates the group when missing (unless --no-create). Each indexed checkout must
    be registered in ~/.gitnexus/registry.json (run gitnexus analyze first). Group
    paths use ``<project>/<repo>``; registry names come from the global registry.
    """
    logger = ctx.obj["logger"]
    config_path = ctx.obj["config_path"]
    app_config = ctx.obj.get("config")
    if app_config is None:
        logger.error("App config missing from CLI context")
        ctx.abort()

    try:
        manager = MetagitConfigManager(config_path=config_path)
        loaded = manager.load_config()
        if isinstance(loaded, Exception):
            raise loaded
        root = workspace_root or str(
            Path(app_config.workspace.path).expanduser().resolve()
        )
        result = GitNexusGroupSyncService().sync_workspace(
            loaded,
            root,
            group_name=group_name,
            create_group=not no_create,
            prune=prune,
            run_contract_sync=not no_contract_sync,
            allow_stale=allow_stale,
            skip_embeddings=skip_embeddings,
            exact_only=exact_only,
            verbose=verbose,
        )
    except Exception as exc:
        logger.error(f"GitNexus group sync failed: {exc}")
        ctx.abort()

    payload = result.model_dump(mode="json")
    if as_json:
        emit_json(payload)
    else:
        click.echo(json.dumps(payload, indent=2))

    for warning in result.warnings:
        logger.warning(warning)
    if result.contract_sync_error:
        logger.error(result.contract_sync_error)

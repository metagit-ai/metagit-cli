#!/usr/bin/env python
"""Top-level repository commands for external node materialization."""

from __future__ import annotations

from pathlib import Path

import click

from metagit.cli.json_output import emit_json
from metagit.core.appconfig.models import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.repo.materialize import RepoMaterializeService
from metagit.core.workspace.root_resolver import resolve_workspace_root


@click.group(name="repo")
@click.pass_context
def repo_group(ctx: click.Context) -> None:
    """Repository operations that are not bound to an already materialized checkout."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@repo_group.command("materialize")
@click.argument("repository")
@click.option("--config-path", "-c", default=".metagit.yml", help="Path to .metagit.yml")
@click.option("--project", "project_name", default=None, help="Workspace project to enroll the repository under.")
@click.option("--dry-run", is_flag=True, help="Resolve and plan without cloning or writing the manifest.")
@click.option("--no-clone", is_flag=True, help="Enroll in the manifest without cloning.")
@click.option("--json", "as_json", is_flag=True, help="Print a JSON envelope.")
@click.pass_context
def repo_materialize(
    ctx: click.Context,
    repository: str,
    config_path: str,
    project_name: str | None,
    dry_run: bool,
    no_clone: bool,
    as_json: bool,
) -> None:
    """Clone an indexed repository and enroll it as a local metagit repository."""
    logger = ctx.obj["logger"]
    app_config: AppConfig = ctx.obj["config"]
    definition = Path(config_path).expanduser()
    loaded = MetagitConfigManager(config_path=str(definition)).load_config()
    if isinstance(loaded, Exception):
        logger.error(str(loaded))
        raise SystemExit(1)
    workspace_root = resolve_workspace_root(str(definition), app_config.workspace.path)
    result = RepoMaterializeService().materialize(
        loaded,
        str(definition),
        repository,
        workspace_root=workspace_root,
        project_name=project_name,
        dry_run=dry_run,
        clone=not no_clone,
    )
    if as_json:
        emit_json(result)
    else:
        if not result.ok and result.error:
            click.echo(f"Error ({result.error.kind}): {result.error.message}", err=True)
        elif result.already_materialized:
            click.echo(f"{result.name} is already materialized as {result.project_name}/{result.name}")
        elif dry_run:
            click.echo(f"Would materialize {result.identity} into {result.project_name}/{result.name}")
            if result.mount_path:
                click.echo(f"  mount: {result.mount_path}")
        else:
            click.echo(f"Materialized {result.name} [{result.identity}]")
            if result.mount_path:
                click.echo(f"  path: {result.mount_path}")
    if not result.ok:
        raise SystemExit(1)

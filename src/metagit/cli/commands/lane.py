#!/usr/bin/env python
"""CLI for evaluating routing promotion state."""

from __future__ import annotations

from pathlib import Path

import click

from metagit.cli.json_output import emit_json
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.routing.routing_service import RoutingService


def _load_manifest(definition_path: str) -> MetagitConfig:
    manager = MetagitConfigManager(definition_path)
    loaded = manager.load_config()
    if isinstance(loaded, Exception):
        raise click.ClickException(str(loaded))
    return loaded


def _load_service(definition_path: str) -> RoutingService:
    config = _load_manifest(definition_path)
    workspace_root = str(Path(definition_path).expanduser().resolve().parent)
    try:
        return RoutingService(config, workspace_root=workspace_root)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


@click.group(name="lane", invoke_without_command=True)
@click.pass_context
def lane_group(ctx: click.Context) -> None:
    """Evaluate lane-tier promotion state from run evidence."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@lane_group.command("eval")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
    help="Path to the workspace .metagit.yml definition file",
)
@click.option("--id", "class_id", default=None)
@click.option("--dry-run", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def lane_eval(definition_path: str, class_id: str | None, dry_run: bool, as_json: bool) -> None:
    """Recompute tier and promotion state from run outcomes."""
    service = _load_service(definition_path)
    try:
        rows = service.evaluate(class_id=class_id, dry_run=dry_run)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    payload = {
        "dry_run": dry_run,
        "updated": [row.model_dump(mode="json", exclude_none=True) for row in rows],
    }
    if as_json:
        emit_json(payload)
        return
    for row in rows:
        click.echo(f"{row.id}\ttier={row.tier}\tstate={row.promotion_state}")

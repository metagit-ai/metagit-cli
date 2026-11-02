#!/usr/bin/env python
"""Workspace graph inspection commands."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

from metagit.cli.json_output import emit_json
from metagit.core.config.composed_view import list_nodes, list_relationships
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.orgindex.store import default_index_home
from metagit.core.repo.neighborhood import GraphNeighborhoodService
from metagit.core.workspace.root_resolver import resolve_definition_root


@click.group(name="graph")
@click.pass_context
def graph_group(ctx: click.Context) -> None:
    """Inspect workspace and organization repository relationships."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@graph_group.command("nodes")
@click.option("--config", "-c", "config_path", default=".metagit.yml", help="Path to .metagit.yml")
@click.option("--json", "as_json", is_flag=True, help="Print JSON records")
@click.pass_context
def graph_nodes(ctx: click.Context, config_path: str, as_json: bool) -> None:
    """List graph nodes from the composed manifest."""
    _emit_records(ctx, list_nodes, config_path, as_json, label="identity")


@graph_group.command("relationships")
@click.option("--config", "-c", "config_path", default=".metagit.yml", help="Path to .metagit.yml")
@click.option("--json", "as_json", is_flag=True, help="Print JSON records")
@click.pass_context
def graph_relationships(ctx: click.Context, config_path: str, as_json: bool) -> None:
    """List graph relationships from the composed manifest."""
    _emit_records(ctx, list_relationships, config_path, as_json, label="id")


def _emit_records(
    ctx: click.Context,
    loader: Callable[[Path], list[dict[str, Any]]],
    config_path: str,
    as_json: bool,
    *,
    label: str,
) -> None:
    _ = ctx
    try:
        records = loader(Path(config_path))
    except Exception as exc:
        raise click.ClickException(str(exc).splitlines()[0]) from exc
    if as_json:
        emit_json(records)
        return
    for record in records:
        click.echo(str(record.get(label) or record.get("name") or record))


@graph_group.command("neighbors")
@click.argument("repository")
@click.option("--config-path", "-c", default=".metagit.yml", help="Path to .metagit.yml")
@click.option("--json", "as_json", is_flag=True, help="Print a JSON envelope.")
@click.pass_context
def graph_neighbors(ctx: click.Context, repository: str, config_path: str, as_json: bool) -> None:
    """Show graph neighbors, including repositories that are only indexed."""
    logger = ctx.obj["logger"]
    definition = Path(config_path).expanduser()
    config = None
    if definition.is_file():
        loaded = MetagitConfigManager(config_path=str(definition)).load_config()
        if isinstance(loaded, Exception):
            logger.error(str(loaded))
            raise SystemExit(1)
        config = loaded
        resolve_definition_root(str(definition))
    result = GraphNeighborhoodService(index_home=default_index_home()).neighbors(config, repository)
    if as_json:
        emit_json(result)
    else:
        if not result.ok:
            click.echo(result.error or "graph neighbors failed", err=True)
        else:
            click.echo(f"{result.name} [{result.presence}]")
            if not result.neighbors:
                click.echo("  (no neighbors)")
            for edge in result.neighbors:
                arrow = "→" if edge.direction == "out" else "←"
                click.echo(f"  {edge.type} {arrow} {edge.name} [{edge.presence}]")
    if not result.ok:
        raise SystemExit(1)

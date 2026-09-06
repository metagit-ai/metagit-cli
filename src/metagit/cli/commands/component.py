#!/usr/bin/env python
"""CLI for component catalog list/show/resolve (RFC-0027)."""

from __future__ import annotations

from typing import Any

import click

from metagit.cli.json_output import emit_json
from metagit.core.component.graph import ComponentGraphService
from metagit.core.component.resolve import ComponentResolver, resolved_component_payload
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.workspace.root_resolver import resolve_definition_root


def _default_manifest(ctx: click.Context) -> str:
    obj = ctx.obj or {}
    definition_path = obj.get("definition_path")
    return str(definition_path) if definition_path else ".metagit.yml"


def _resolve_manifest_path(ctx: click.Context, config_path: str | None) -> str:
    if config_path:
        return config_path
    stored = (ctx.obj or {}).get("component_manifest")
    return str(stored) if stored else _default_manifest(ctx)


def _load_config(manifest_path: str) -> MetagitConfig:
    manager = MetagitConfigManager(config_path=manifest_path)
    loaded = manager.load_config()
    if isinstance(loaded, Exception):
        raise click.ClickException(str(loaded))
    return loaded


def _resolver_context(
    ctx: click.Context,
    config_path: str | None,
) -> tuple[MetagitConfig, str]:
    manifest_path = _resolve_manifest_path(ctx, config_path)
    return _load_config(manifest_path), resolve_definition_root(manifest_path)


@click.group(name="component")
@click.option(
    "--config-path",
    "-c",
    "config_path",
    default=None,
    help="Path to the metagit configuration file",
)
@click.pass_context
def component_group(ctx: click.Context, config_path: str | None) -> None:
    """List, show, resolve, and graph catalogued components."""
    ctx.ensure_object(dict)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return
    ctx.obj["component_manifest"] = config_path or _default_manifest(ctx)


@component_group.command("list")
@click.option(
    "--config-path",
    "-c",
    "config_path",
    default=None,
    help="Path to the metagit configuration file",
)
@click.option("--project", default=None)
@click.option("--repo", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def component_list(
    ctx: click.Context,
    config_path: str | None,
    project: str | None,
    repo: str | None,
    as_json: bool,
) -> None:
    """List catalogued components, optionally filtered by project/repo."""
    config, _ = _resolver_context(ctx, config_path)
    rows = ComponentResolver().list(config, project=project, repo=repo)
    if as_json:
        emit_json({"components": [resolved_component_payload(row) for row in rows]})
        return
    for row in rows:
        kind = row.spec.kind or "-"
        click.echo(f"{row.id}\t{row.spec.path}\t{kind}")


@component_group.command("show")
@click.argument("identity")
@click.option(
    "--config-path",
    "-c",
    "config_path",
    default=None,
    help="Path to the metagit configuration file",
)
@click.option("--project", default=None)
@click.option("--repo", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def component_show(
    ctx: click.Context,
    identity: str,
    config_path: str | None,
    project: str | None,
    repo: str | None,
    as_json: bool,
) -> None:
    """Show one component by project/repo/component id or unique name."""
    config, _ = _resolver_context(ctx, config_path)
    result = ComponentResolver().get(config, identity, project=project, repo=repo)
    if isinstance(result, ValueError):
        raise click.ClickException(str(result))
    if result is None:
        click.echo(f"component not found: {identity}", err=True)
        raise SystemExit(1)
    payload = resolved_component_payload(result)
    if as_json:
        emit_json(payload)
        return
    kind = result.spec.kind or "-"
    click.echo(f"{result.id}\t{result.spec.path}\t{kind}")


@component_group.command("resolve")
@click.argument("path")
@click.option(
    "--config-path",
    "-c",
    "config_path",
    default=None,
    help="Path to the metagit configuration file",
)
@click.option("--project", default=None)
@click.option("--repo", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def component_resolve(
    ctx: click.Context,
    path: str,
    config_path: str | None,
    project: str | None,
    repo: str | None,
    as_json: bool,
) -> None:
    """Run component resolve for a path to the longest-matching catalogued component."""
    config, definition_root = _resolver_context(ctx, config_path)
    result = ComponentResolver().resolve(
        config,
        path,
        project=project,
        repo=repo,
        definition_root=definition_root,
    )
    if isinstance(result, ValueError):
        raise click.ClickException(str(result))
    if result is None:
        payload: dict[str, Any] = {"matched": False, "path": path}
        if as_json:
            emit_json(payload)
        else:
            click.echo(f"no component matched: {path}", err=True)
        raise SystemExit(1)
    payload = {"matched": True, **resolved_component_payload(result), "path": path}
    if as_json:
        emit_json(payload)
        return
    click.echo(f"{result.id}\t{result.spec.path}")


@component_group.command("graph")
@click.argument("identity")
@click.option(
    "--config-path",
    "-c",
    "config_path",
    default=None,
    help="Path to the metagit configuration file",
)
@click.option("--project", default=None)
@click.option("--repo", default=None)
@click.option("--depth", type=int, default=1)
@click.option(
    "--direction",
    type=click.Choice(["out", "in", "both"], case_sensitive=True),
    default="out",
)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def component_graph(
    ctx: click.Context,
    identity: str,
    config_path: str | None,
    project: str | None,
    repo: str | None,
    depth: int,
    direction: str,
    as_json: bool,
) -> None:
    """Run component graph neighborhood walk from a catalog identity."""
    config, _ = _resolver_context(ctx, config_path)
    result = ComponentGraphService().neighborhood(
        config,
        identity,
        project=project,
        repo=repo,
        depth=depth,
        direction=direction,  # type: ignore[arg-type]
    )
    if isinstance(result, ValueError):
        raise click.ClickException(str(result))
    if result is None:
        click.echo(f"component not found: {identity}", err=True)
        raise SystemExit(1)
    if as_json:
        emit_json(result)
        return
    click.echo(result["origin"]["id"])
    for edge in result["edges"]:
        click.echo(f"{edge['from']} --{edge['type']}--> {edge['to']}")

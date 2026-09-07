#!/usr/bin/env python
"""CLI for component catalog list/show/resolve/graph plus component detect and component init."""

from __future__ import annotations

from typing import Any

import click

from metagit.cli.json_output import emit_json
from metagit.core.component.detect import ComponentDetector
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
) -> tuple[MetagitConfig, str, str]:
    manifest_path = _resolve_manifest_path(ctx, config_path)
    return _load_config(manifest_path), resolve_definition_root(manifest_path), manifest_path


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
    """List, show, resolve, graph, detect, and init catalogued components."""
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
    config, _, _ = _resolver_context(ctx, config_path)
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
    config, _, _ = _resolver_context(ctx, config_path)
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
    config, definition_root, _ = _resolver_context(ctx, config_path)
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
    config, _, _ = _resolver_context(ctx, config_path)
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


@component_group.command("detect")
@click.option(
    "--config-path",
    "-c",
    "config_path",
    default=None,
    help="Path to the metagit configuration file",
)
@click.option("--project", default=None)
@click.option("--repo", default=None)
@click.option("--apply", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def component_detect(
    ctx: click.Context,
    config_path: str | None,
    project: str | None,
    repo: str | None,
    apply: bool,
    as_json: bool,
) -> None:
    """Run component detect for filesystem marker candidates (read-only without --apply)."""
    config, definition_root, manifest_path = _resolver_context(ctx, config_path)
    detector = ComponentDetector()
    payload = detector.detect(
        config,
        project=project,
        repo=repo,
        definition_root=definition_root,
    )
    if apply:
        saved = detector.apply_candidates(
            config,
            payload["candidates"],
            config_path=manifest_path,
        )
        if isinstance(saved, Exception):
            raise click.ClickException(str(saved))
    if as_json:
        emit_json(payload)
        return
    if not payload["candidates"]:
        click.echo("no component candidates")
        return
    for row in payload["candidates"]:
        kind = row.get("kind") or "-"
        confidence = row.get("confidence") or "-"
        flagged = "catalogued" if row.get("already_catalogued") else "new"
        click.echo(f"{row['name']}\t{row['path']}\t{kind}\t{confidence}\t{flagged}")


@component_group.command("init")
@click.argument("path")
@click.option(
    "--config-path",
    "-c",
    "config_path",
    default=None,
    help="Path to the metagit configuration file",
)
@click.option("--name", default=None)
@click.option("--kind", default=None)
@click.option("--project", default=None)
@click.option("--repo", default=None)
@click.option("--apply", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def component_init(
    ctx: click.Context,
    path: str,
    config_path: str | None,
    name: str | None,
    kind: str | None,
    project: str | None,
    repo: str | None,
    apply: bool,
    as_json: bool,
) -> None:
    """Run component init for one declarative repository-relative path."""
    config, _, manifest_path = _resolver_context(ctx, config_path)
    detector = ComponentDetector()
    created = detector.init_component(
        config,
        path,
        name=name,
        kind=kind,
        project=project,
        repo=repo,
    )
    if isinstance(created, ValueError):
        raise click.ClickException(str(created))
    target = detector._unique_target(config, project=project, repo=repo)
    if isinstance(target, ValueError):
        raise click.ClickException(str(target))
    project_name, repo_name = target
    if apply:
        saved = detector.apply_candidates(
            config,
            [
                {
                    "name": created.name,
                    "path": created.path,
                    "kind": created.kind,
                    "language": created.language,
                    "project": project_name,
                    "repo": repo_name,
                    "already_catalogued": False,
                }
            ],
            config_path=manifest_path,
        )
        if isinstance(saved, Exception):
            raise click.ClickException(str(saved))
    payload = {
        "name": created.name,
        "path": created.path,
        "kind": created.kind,
        "language": created.language,
        "project": project_name,
        "repo": repo_name,
        "applied": apply,
    }
    if as_json:
        emit_json(payload)
        return
    click.echo(f"{created.name}\t{created.path}\t{created.kind or '-'}")

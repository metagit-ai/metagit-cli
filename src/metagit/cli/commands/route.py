#!/usr/bin/env python
"""CLI for routing class discovery and inspection."""

from __future__ import annotations

from pathlib import Path

import click

from metagit.cli.json_output import emit_json
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.routing.models import RequestClass, Run
from metagit.core.routing.router import MatchResult
from metagit.core.routing.routing_service import RoutingService


def _load_manifest(definition_path: str) -> MetagitConfig:
    manager = MetagitConfigManager(definition_path)
    loaded = manager.load_config()
    if isinstance(loaded, Exception):
        raise click.ClickException(str(loaded))
    return loaded


def _load_service(definition_path: str) -> tuple[RoutingService, MetagitConfig]:
    config = _load_manifest(definition_path)
    workspace_root = str(Path(definition_path).expanduser().resolve().parent)
    try:
        service = RoutingService(config, workspace_root=workspace_root)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    return service, config


def _match_payload(match: MatchResult) -> dict[str, object]:
    return {
        "id": match.request_class.id,
        "title": match.request_class.title,
        "confidence": match.confidence,
        "why": match.why,
        "class": match.request_class.model_dump(mode="json", exclude_none=True),
    }


def _class_payload(row: RequestClass) -> dict[str, object]:
    return row.model_dump(mode="json", exclude_none=True)


def _run_payload(row: Run) -> dict[str, object]:
    return row.model_dump(mode="json", by_alias=True, exclude_none=True)


@click.group(name="route", invoke_without_command=True)
@click.pass_context
def route_group(ctx: click.Context) -> None:
    """Query and inspect routing request classes."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@route_group.command("query")
@click.argument("ask")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
    help="Path to the workspace .metagit.yml definition file",
)
@click.option("--limit", type=click.IntRange(min=1), default=5, show_default=True)
@click.option("--json", "as_json", is_flag=True)
def route_query(ask: str, definition_path: str, limit: int, as_json: bool) -> None:
    """Resolve a natural-language ask to ranked request classes."""
    service, config = _load_service(definition_path)
    matches = service.query(ask, limit=limit)

    if not matches:
        prefix = "REQ"
        if config.routing is not None:
            prefix = config.routing.id_prefix
        message = (
            f"No routing class matched this ask. If it recurs, catalog a new {prefix}-... class under routing.catalog."
        )
        if as_json:
            emit_json({"ok": False, "ask": ask, "matches": [], "error": message})
            raise SystemExit(1)
        raise click.ClickException(message)

    payload = {
        "ok": True,
        "ask": ask,
        "count": len(matches),
        "matches": [_match_payload(item) for item in matches],
    }
    if as_json:
        emit_json(payload)
        return
    for item in payload["matches"]:
        click.echo(
            f"{item['id']}\tconfidence={item['confidence']:.3f}\ttier={item['class']['tier']}\t{item['title']}",
        )


@route_group.command("list")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
    help="Path to the workspace .metagit.yml definition file",
)
@click.option(
    "--tier",
    type=click.Choice(["deterministic", "skilled", "novel"], case_sensitive=True),
    default=None,
)
@click.option("--ready", is_flag=True, help="Only show classes waiting on executor promotion")
@click.option("--json", "as_json", is_flag=True)
def route_list(definition_path: str, tier: str | None, ready: bool, as_json: bool) -> None:
    """List routing classes with optional tier and readiness filters."""
    service, _ = _load_service(definition_path)
    rows = service.list_classes(tier=tier, ready=ready)
    if as_json:
        emit_json({"classes": [_class_payload(row) for row in rows]})
        return
    for row in rows:
        click.echo(f"{row.id}\t{row.tier}\t{row.promotion_state}\t{row.title}")


@route_group.command("show")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
    help="Path to the workspace .metagit.yml definition file",
)
@click.option("--id", "class_id", required=True)
@click.option("--json", "as_json", is_flag=True)
def route_show(definition_path: str, class_id: str, as_json: bool) -> None:
    """Show one class plus run history."""
    service, _ = _load_service(definition_path)
    try:
        result = service.show_class(class_id)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    request_class = result["class"]
    runs = result["runs"]
    payload = {
        "class": _class_payload(request_class),
        "runs": [_run_payload(run) for run in runs],
        "run_count": result["run_count"],
    }
    if as_json:
        emit_json(payload)
        return
    click.echo(
        f"{request_class.id}\t{request_class.tier}\t{request_class.promotion_state}\truns={result['run_count']}",
    )

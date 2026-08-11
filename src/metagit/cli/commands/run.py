#!/usr/bin/env python
"""CLI for routing run ledger lifecycle operations."""

from __future__ import annotations

from pathlib import Path

import click

from metagit.cli.json_output import emit_json
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.routing.models import Run
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


def _run_payload(row: Run) -> dict[str, object]:
    return row.model_dump(mode="json", by_alias=True, exclude_none=True)


@click.group(name="run", invoke_without_command=True)
@click.pass_context
def run_group(ctx: click.Context) -> None:
    """Open, close, and list routing run records."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@run_group.command("open")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
    help="Path to the workspace .metagit.yml definition file",
)
@click.option("--class", "class_id", required=True)
@click.option("--actor", required=True)
@click.option(
    "--tier",
    type=click.Choice(["deterministic", "skilled", "novel"], case_sensitive=True),
    default=None,
)
@click.option("--lane", default=None)
@click.option("--objective", default=None)
@click.option("--session-id", default=None)
@click.option("--branch", default=None)
@click.option("--workdir", default=None)
@click.option("--doctrine-chars", type=click.IntRange(min=0), default=None)
@click.option("--json", "as_json", is_flag=True)
def run_open(
    definition_path: str,
    class_id: str,
    actor: str,
    tier: str | None,
    lane: str | None,
    objective: str | None,
    session_id: str | None,
    branch: str | None,
    workdir: str | None,
    doctrine_chars: int | None,
    as_json: bool,
) -> None:
    """Open a run for a request class."""
    service = _load_service(definition_path)
    try:
        row = service.open_run(
            class_id=class_id,
            actor=actor,
            tier=tier,
            lane=lane,
            objective=objective,
            session_id=session_id,
            branch=branch,
            workdir=workdir,
            doctrine_chars=doctrine_chars,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        emit_json(row.model_dump(mode="json", by_alias=True, exclude_none=True))
        return
    click.echo(f"{row.id}\tclass={row.cls}\ttier={row.tier}\topened={row.opened}")


@run_group.command("close")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
    help="Path to the workspace .metagit.yml definition file",
)
@click.option("--id", "run_id", required=True)
@click.option(
    "--outcome",
    required=True,
    type=click.Choice(["landed", "bounced", "noop", "abandoned"], case_sensitive=True),
)
@click.option("--mr-url", default=None)
@click.option("--gate", "gates", multiple=True)
@click.option("--evidence-file", default=None)
@click.option("--json", "as_json", is_flag=True)
def run_close(
    definition_path: str,
    run_id: str,
    outcome: str,
    mr_url: str | None,
    gates: tuple[str, ...],
    evidence_file: str | None,
    as_json: bool,
) -> None:
    """Close one open run with an outcome and optional evidence."""
    service = _load_service(definition_path)
    try:
        row = service.close_run(
            run_id=run_id,
            outcome=outcome,
            mr_url=mr_url,
            gates=list(gates),
            evidence_file=evidence_file,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        emit_json(row.model_dump(mode="json", by_alias=True, exclude_none=True))
        return
    click.echo(f"{row.id}\toutcome={row.outcome}\tclosed={row.closed}")


@run_group.command("list")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
    help="Path to the workspace .metagit.yml definition file",
)
@click.option("--class", "class_id", default=None)
@click.option(
    "--outcome",
    default=None,
    type=click.Choice(["landed", "bounced", "noop", "abandoned"], case_sensitive=True),
)
@click.option("--open", "open_only", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def run_list(
    definition_path: str,
    class_id: str | None,
    outcome: str | None,
    open_only: bool,
    as_json: bool,
) -> None:
    """List runs with optional filters."""
    service = _load_service(definition_path)
    rows = service.list_runs(class_id=class_id, outcome=outcome, open_only=open_only)
    if as_json:
        emit_json({"runs": [_run_payload(row) for row in rows]})
        return
    for row in rows:
        status = row.outcome or "open"
        click.echo(f"{row.id}\tclass={row.cls}\tstatus={status}\ttier={row.tier}")

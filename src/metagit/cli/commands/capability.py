#!/usr/bin/env python
"""CLI for capability resolve/compile workflows."""

from __future__ import annotations

from pathlib import Path

import click

from metagit.cli.json_output import emit_json
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.routing.capability_service import CapabilityService


def _load_manifest(definition_path: str) -> MetagitConfig:
    manager = MetagitConfigManager(definition_path)
    loaded = manager.load_config()
    if isinstance(loaded, Exception):
        raise click.ClickException(str(loaded))
    return loaded


def _load_service(definition_path: str) -> CapabilityService:
    config = _load_manifest(definition_path)
    workspace_root = str(Path(definition_path).expanduser().resolve().parent)
    return CapabilityService(config, workspace_root=workspace_root)


def _json_error(code: str, message: str) -> None:
    emit_json({"ok": False, "error": code, "message": message})
    raise SystemExit(1)


@click.group(name="capability", invoke_without_command=True)
@click.pass_context
def capability_group(ctx: click.Context) -> None:
    """Resolve and compile capability envelopes."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@capability_group.command("list")
@click.option("--definition", "-c", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--project", default=None)
@click.option("--json", "as_json", is_flag=True)
def capability_list(definition_path: str, project: str | None, as_json: bool) -> None:
    """List request classes that define a capability block."""
    service = _load_service(definition_path)
    rows = service.list_capabilities(project=project)
    payload = {"ok": True, "count": len(rows), "capabilities": [row.model_dump(mode="json") for row in rows]}
    if as_json:
        emit_json(payload)
        return
    for row in rows:
        click.echo(f"{row.id}\t{row.title}")


@capability_group.command("resolve")
@click.argument("ask")
@click.option("--definition", "-c", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--project", default=None)
@click.option("--repo", default=None)
@click.option("--limit", type=click.IntRange(min=1), default=5, show_default=True)
@click.option("--json", "as_json", is_flag=True)
def capability_resolve(
    ask: str,
    definition_path: str,
    project: str | None,
    repo: str | None,
    limit: int,
    as_json: bool,
) -> None:
    """Resolve ask text to ranked capability candidates."""
    service = _load_service(definition_path)
    matches = service.resolve(ask, project=project, repo=repo, limit=limit)
    if not matches:
        if as_json:
            _json_error("no_capability_match", "No capability matched this ask and selector scope")
        raise click.ClickException("No capability matched this ask and selector scope")
    payload = {"ok": True, "count": len(matches), "matches": [row.model_dump(mode="json") for row in matches]}
    if as_json:
        emit_json(payload)
        return
    for row in matches:
        click.echo(f"{row.capability_id}\tconfidence={row.confidence:.3f}\t{row.why}")


@capability_group.command("show")
@click.option("--definition", "-c", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--id", "capability_id", required=True)
@click.option("--json", "as_json", is_flag=True)
def capability_show(definition_path: str, capability_id: str, as_json: bool) -> None:
    """Show one capability class plus run history."""
    service = _load_service(definition_path)
    try:
        payload = service.show_capability(capability_id)
    except ValueError as exc:
        if as_json:
            _json_error(str(exc), f"Capability {capability_id} not found")
        raise click.ClickException(f"Capability {capability_id} not found") from exc
    if as_json:
        emit_json(payload)
        return
    click.echo(f"{capability_id}\truns={payload['run_count']}")


@capability_group.command("compile")
@click.option("--definition", "-c", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--id", "capability_id", required=True)
@click.option("--project", required=True)
@click.option("--repo", default=None)
@click.option("--task-id", default=None)
@click.option("--graph-id", default=None)
@click.option("--objective-id", default=None)
@click.option("--tier", type=click.IntRange(0, 2), default=1, show_default=True)
@click.option("--budget", type=click.IntRange(min=1), default=None)
@click.option("--no-context", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
def capability_compile(
    definition_path: str,
    capability_id: str,
    project: str,
    repo: str | None,
    task_id: str | None,
    graph_id: str | None,
    objective_id: str | None,
    tier: int,
    budget: int | None,
    no_context: bool,
    as_json: bool,
) -> None:
    """Compile a capability envelope for one project/repo."""
    service = _load_service(definition_path)
    try:
        envelope = service.compile(
            capability_id,
            project=project,
            repo=repo,
            task_id=task_id,
            graph_id=graph_id,
            objective_id=objective_id,
            tier=tier,  # type: ignore[arg-type]
            budget=budget,
            with_context=not no_context,
        )
    except ValueError as exc:
        code = str(exc).split(":", 1)[0]
        if as_json:
            _json_error(code, str(exc))
        raise click.ClickException(str(exc)) from exc
    if as_json:
        emit_json(envelope)
        return
    click.echo(f"capability: {envelope.capability_id}")
    click.echo(f"repo: {envelope.repository.project}/{envelope.repository.repo}")
    click.echo(f"cwd: {envelope.cwd}")


@capability_group.command("doctor")
@click.option("--definition", "-c", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--json", "as_json", is_flag=True)
def capability_doctor(definition_path: str, as_json: bool) -> None:
    """Validate capability selector and workflow constraints."""
    service = _load_service(definition_path)
    result = service.doctor()
    if as_json:
        emit_json(result)
        if not result["ok"]:
            raise SystemExit(1)
        return
    if result["ok"]:
        click.echo("capability doctor: ok")
        return
    click.echo("capability doctor: issues")
    for issue in result["issues"]:
        click.echo(f"- {issue['id']}: {issue['error']} ({issue['message']})")
    raise SystemExit(1)

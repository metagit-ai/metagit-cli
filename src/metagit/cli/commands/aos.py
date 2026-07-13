#!/usr/bin/env python
"""CLI for Agent Operating System composition façade (RFC-0013)."""

from __future__ import annotations

from typing import Optional

import click

from metagit.cli.commands.acl_common import emit_json, raise_if_error, resolve_acl_roots
from metagit.core.aos.service import AosService


@click.group(name="aos")
@click.pass_context
def aos_group(ctx: click.Context) -> None:
    """Agent Operating System composition façade (RFC-0013)."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def _service(ctx: click.Context, definition_path: str) -> AosService:
    roots = resolve_acl_roots(ctx, definition_path)
    return AosService(roots.session_root)


@aos_group.command("status")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def aos_status(ctx: click.Context, definition_path: str, as_json: bool) -> None:
    """Show aggregated coordination subsystem status."""
    service = _service(ctx, definition_path)
    result = raise_if_error(service.status())
    if as_json:
        emit_json(result)
        return
    for name, section in result.subsystems.items():
        flag = "ok" if section.available else "missing"
        click.echo(f"{name}\t{flag}")


@aos_group.command("doctor")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--fix", "do_fix", is_flag=True, help="Run safe ACL GC (requires --yes)")
@click.option("--yes", "confirm", is_flag=True, help="Confirm --fix mutations")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def aos_doctor(
    ctx: click.Context,
    definition_path: str,
    do_fix: bool,
    confirm: bool,
    as_json: bool,
) -> None:
    """Report coordination health; optionally run safe ACL GC."""
    service = _service(ctx, definition_path)
    result = raise_if_error(service.doctor(fix=do_fix, confirm=confirm))
    if as_json:
        emit_json(result)
        return
    for finding in result.findings:
        click.echo(f"{finding.severity}\t{finding.code}\t{finding.message}")
    for cmd in result.suggested_commands:
        click.echo(f"suggest\t{cmd}")
    for item in result.fixed:
        click.echo(f"fixed\t{item}")


@aos_group.command("next")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--graph-id", default=None)
@click.option("--commit", "do_commit", is_flag=True, help="Record schedule decision")
@click.option("--apply-hints", is_flag=True, help="Apply ACL bind APIs for the chosen node")
@click.option("--agent-id", default=None, help="Required with --apply-hints")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def aos_next(
    ctx: click.Context,
    definition_path: str,
    graph_id: Optional[str],
    do_commit: bool,
    apply_hints: bool,
    agent_id: Optional[str],
    as_json: bool,
) -> None:
    """Preview or commit the next composed work envelope."""
    service = _service(ctx, definition_path)
    result = raise_if_error(
        service.next(
            commit=do_commit,
            apply_hints=apply_hints,
            agent_id=agent_id,
            graph_id=graph_id,
        )
    )
    if as_json:
        emit_json(result)
        return
    node = (result.decision or {}).get("node_id") if result.decision else None
    click.echo(
        f"committed={result.committed} hints_applied={result.hints_applied} "
        f"scheduler={result.scheduler_available} node={node or '-'}"
    )
    if result.compile_command:
        click.echo(f"compile\t{result.compile_command}")
    for cmd in result.acl_commands:
        click.echo(f"acl\t{cmd}")

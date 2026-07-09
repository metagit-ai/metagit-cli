#!/usr/bin/env python
"""CLI for advisory ACL file claims (RFC-0007)."""

from __future__ import annotations

from typing import Optional

import click

from metagit.cli.commands.acl_common import emit_json, raise_if_error, resolve_acl_roots
from metagit.core.coordination.claim_service import ClaimService
from metagit.core.coordination.models import ClaimCheckResult, FileClaim


@click.group(name="claim")
@click.pass_context
def claim_group(ctx: click.Context) -> None:
    """Manage advisory file-path claims."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@claim_group.command("declare")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--repository", required=True)
@click.option("--agent-id", required=True)
@click.option("--pattern", "patterns", multiple=True, required=True)
@click.option("--task-id", default=None)
@click.option("--strict", is_flag=True, help="Fail when overlapping claims exist")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def claim_declare(
    ctx: click.Context,
    definition_path: str,
    repository: str,
    agent_id: str,
    patterns: tuple[str, ...],
    task_id: Optional[str],
    strict: bool,
    as_json: bool,
) -> None:
    """Declare advisory file claims before coding."""
    session_root = resolve_acl_roots(ctx, definition_path).session_root
    service = ClaimService(session_root)
    result = service.declare(
        repository=repository,
        agent_id=agent_id,
        patterns=list(patterns),
        task_id=task_id,
        allow_conflicts=not strict,
    )
    if isinstance(result, Exception):
        raise click.ClickException(str(result))
    if isinstance(result, ClaimCheckResult):
        if as_json:
            emit_json(result)
            raise SystemExit(2)
        click.echo("Conflict")
        for conflict in result.conflicts:
            click.echo(f"Owner:\t{conflict.owner}")
            click.echo("Files:")
            for path in conflict.files:
                click.echo(f"  {path}")
        raise SystemExit(2)
    assert isinstance(result, FileClaim)
    if as_json:
        emit_json(result)
        return
    click.echo(f"{result.claim_id}\t{result.repository}\t{','.join(result.patterns)}")


@claim_group.command("check")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--repository", required=True)
@click.option("--pattern", "patterns", multiple=True, required=True)
@click.option("--agent-id", default=None, help="Ignore this agent's own claims")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def claim_check(
    ctx: click.Context,
    definition_path: str,
    repository: str,
    patterns: tuple[str, ...],
    agent_id: Optional[str],
    as_json: bool,
) -> None:
    """Check for overlapping advisory claims."""
    session_root = resolve_acl_roots(ctx, definition_path).session_root
    service = ClaimService(session_root)
    result = raise_if_error(
        service.check(repository=repository, patterns=list(patterns), agent_id=agent_id),
    )
    if as_json:
        emit_json(result)
        return
    if not result.conflicts:
        click.echo("No conflicts.")
        return
    for conflict in result.conflicts:
        click.echo(f"Owner:\t{conflict.owner}")
        for path in conflict.files:
            click.echo(f"  {path}")


@claim_group.command("list")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--repository", default=None)
@click.option("--agent-id", default=None)
@click.option("--status", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def claim_list(
    ctx: click.Context,
    definition_path: str,
    repository: Optional[str],
    agent_id: Optional[str],
    status: Optional[str],
    as_json: bool,
) -> None:
    """List file claims."""
    session_root = resolve_acl_roots(ctx, definition_path).session_root
    service = ClaimService(session_root)
    result = raise_if_error(
        service.list(repository=repository, agent_id=agent_id, status=status),
    )
    if as_json:
        emit_json(result)
        return
    if not result.claims:
        click.echo("No claims.")
        return
    for row in result.claims:
        click.echo(
            f"{row.claim_id}\t{row.agent_id}\t{row.repository}\t{row.status}\t{','.join(row.patterns)}",
        )


@claim_group.command("release")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--claim-id", required=True)
@click.option("--agent-id", required=True)
@click.option("--force", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def claim_release(
    ctx: click.Context,
    definition_path: str,
    claim_id: str,
    agent_id: str,
    force: bool,
    as_json: bool,
) -> None:
    """Release an advisory file claim."""
    session_root = resolve_acl_roots(ctx, definition_path).session_root
    service = ClaimService(session_root)
    result = raise_if_error(
        service.release(claim_id=claim_id, agent_id=agent_id, force=force),
    )
    if as_json:
        emit_json(result)
        return
    click.echo(f"released\t{result.claim_id}")

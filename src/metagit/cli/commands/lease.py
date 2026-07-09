#!/usr/bin/env python
"""CLI for ACL branch leases (RFC-0007). Distinct from handoff claim TTL leases."""

from __future__ import annotations

from typing import Optional

import click

from metagit.cli.commands.acl_common import emit_json, raise_if_error, resolve_acl_roots
from metagit.core.coordination.lease_service import DEFAULT_LEASE_TTL, LeaseService


@click.group(name="lease")
@click.pass_context
def lease_group(ctx: click.Context) -> None:
    """Manage ACL branch leases (not handoff claim leases)."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@lease_group.command("acquire")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--repository", required=True, help="project/repo")
@click.option("--agent-id", required=True)
@click.option("--task-id", required=True)
@click.option("--branch", default=None, help="Allocated agent/* branch name")
@click.option("--branch-id", default=None)
@click.option("--ttl", default=DEFAULT_LEASE_TTL, show_default=True)
@click.option("--allocate", "allocate_if_missing", is_flag=True, help="Allocate branch if missing")
@click.option("--description", default=None)
@click.option("--integration-branch", default=None)
@click.option("--base", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def lease_acquire(
    ctx: click.Context,
    definition_path: str,
    repository: str,
    agent_id: str,
    task_id: str,
    branch: Optional[str],
    branch_id: Optional[str],
    ttl: str,
    allocate_if_missing: bool,
    description: Optional[str],
    integration_branch: Optional[str],
    base: Optional[str],
    as_json: bool,
) -> None:
    """Acquire a branch lease for an agent."""
    session_root, sync_root, definition = resolve_acl_roots(ctx, definition_path)
    service = LeaseService(session_root, sync_root=sync_root, definition_path=definition)
    result = raise_if_error(
        service.acquire(
            repository=repository,
            agent_id=agent_id,
            task_id=task_id,
            branch=branch,
            branch_id=branch_id,
            ttl=ttl,
            allocate_if_missing=allocate_if_missing,
            description=description,
            integration_branch=integration_branch,
            base=base,
        ),
    )
    if as_json:
        emit_json(result)
        return
    click.echo(
        f"{result.lease_id}\t{result.branch}\t{result.repository}\t"
        f"{result.agent_id}\t{result.expires}\t{result.status}",
    )


@lease_group.command("renew")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--lease-id", required=True)
@click.option("--agent-id", required=True)
@click.option("--ttl", default=DEFAULT_LEASE_TTL, show_default=True)
@click.option("--force", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def lease_renew(
    ctx: click.Context,
    definition_path: str,
    lease_id: str,
    agent_id: str,
    ttl: str,
    force: bool,
    as_json: bool,
) -> None:
    """Renew an ACL branch lease."""
    session_root, sync_root, definition = resolve_acl_roots(ctx, definition_path)
    service = LeaseService(session_root, sync_root=sync_root, definition_path=definition)
    result = raise_if_error(
        service.renew(lease_id=lease_id, agent_id=agent_id, ttl=ttl, force=force),
    )
    if as_json:
        emit_json(result)
        return
    click.echo(f"renewed\t{result.lease_id}\t{result.expires}")


@lease_group.command("release")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--lease-id", required=True)
@click.option("--agent-id", required=True)
@click.option("--force", is_flag=True)
@click.option("--release-branch", is_flag=True, help="Also mark branch allocation released")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def lease_release(
    ctx: click.Context,
    definition_path: str,
    lease_id: str,
    agent_id: str,
    force: bool,
    release_branch: bool,
    as_json: bool,
) -> None:
    """Release an ACL branch lease."""
    session_root, sync_root, definition = resolve_acl_roots(ctx, definition_path)
    service = LeaseService(session_root, sync_root=sync_root, definition_path=definition)
    result = raise_if_error(
        service.release(
            lease_id=lease_id,
            agent_id=agent_id,
            force=force,
            release_branch=release_branch,
        ),
    )
    if as_json:
        emit_json(result)
        return
    click.echo(f"released\t{result.lease_id}\t{result.branch}")


@lease_group.command("list")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--repository", default=None)
@click.option("--status", default=None)
@click.option("--agent-id", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def lease_list(
    ctx: click.Context,
    definition_path: str,
    repository: Optional[str],
    status: Optional[str],
    agent_id: Optional[str],
    as_json: bool,
) -> None:
    """List ACL branch leases and advisory repo presence."""
    session_root, sync_root, definition = resolve_acl_roots(ctx, definition_path)
    service = LeaseService(session_root, sync_root=sync_root, definition_path=definition)
    result = raise_if_error(
        service.list(repository=repository, status=status, agent_id=agent_id),
    )
    if as_json:
        emit_json(result)
        return
    if not result.leases:
        click.echo("No leases.")
    for row in result.leases:
        click.echo(
            f"{row.lease_id}\t{row.branch}\t{row.repository}\t{row.agent_id}\t{row.status}\t{row.expires}",
        )
    if result.presence:
        click.echo("--- presence ---")
        for item in result.presence:
            click.echo(f"{item.repository}\t{','.join(item.agent_ids)}")

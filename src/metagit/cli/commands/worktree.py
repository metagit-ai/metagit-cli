#!/usr/bin/env python
"""CLI for ACL worktree management (RFC-0007)."""

from __future__ import annotations

from typing import Optional

import click

from metagit.cli.commands.acl_common import emit_json, raise_if_error, resolve_acl_roots
from metagit.core.coordination.worktree_service import WorktreeService


@click.group(name="worktree")
@click.pass_context
def worktree_group(ctx: click.Context) -> None:
    """Manage isolated agent git worktrees."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@worktree_group.command("create")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--repository", required=True, help="project/repo")
@click.option("--agent-id", required=True)
@click.option("--task-id", required=True)
@click.option("--branch", required=True)
@click.option("--lease-id", default=None)
@click.option("--integration-branch", default=None)
@click.option("--claim", "claims", multiple=True, help="Optional claim pattern to record on manifest")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def worktree_create(
    ctx: click.Context,
    definition_path: str,
    repository: str,
    agent_id: str,
    task_id: str,
    branch: str,
    lease_id: Optional[str],
    integration_branch: Optional[str],
    claims: tuple[str, ...],
    as_json: bool,
) -> None:
    """Create an isolated worktree for an agent with an active lease."""
    session_root, sync_root, definition = resolve_acl_roots(ctx, definition_path)
    service = WorktreeService(session_root, sync_root=sync_root, definition_path=definition)
    result = raise_if_error(
        service.create(
            repository=repository,
            agent_id=agent_id,
            task_id=task_id,
            branch=branch,
            lease_id=lease_id,
            integration_branch=integration_branch,
            claims=list(claims) or None,
        ),
    )
    if as_json:
        emit_json(result)
        return
    click.echo(f"{result.worktree_id}\t{result.path}\t{result.branch}\t{result.status}")


@worktree_group.command("destroy")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--worktree-id", default=None)
@click.option("--agent-id", default=None)
@click.option("--repository", default=None)
@click.option("--force", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def worktree_destroy(
    ctx: click.Context,
    definition_path: str,
    worktree_id: Optional[str],
    agent_id: Optional[str],
    repository: Optional[str],
    force: bool,
    as_json: bool,
) -> None:
    """Destroy an agent worktree."""
    session_root, sync_root, definition = resolve_acl_roots(ctx, definition_path)
    service = WorktreeService(session_root, sync_root=sync_root, definition_path=definition)
    result = raise_if_error(
        service.destroy(
            worktree_id=worktree_id,
            agent_id=agent_id,
            repository=repository,
            force=force,
        ),
    )
    if as_json:
        emit_json(result)
        return
    click.echo(f"destroyed\t{result.worktree_id}\t{result.path}")


@worktree_group.command("gc")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def worktree_gc(ctx: click.Context, definition_path: str, as_json: bool) -> None:
    """Garbage-collect worktrees with expired leases or missing paths."""
    session_root, sync_root, definition = resolve_acl_roots(ctx, definition_path)
    service = WorktreeService(session_root, sync_root=sync_root, definition_path=definition)
    result = raise_if_error(service.gc())
    if as_json:
        emit_json({"ok": True, "destroyed": [row.model_dump(mode="json") for row in result]})
        return
    click.echo(f"gc destroyed {len(result)} worktree(s)")


@worktree_group.command("status")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--worktree-id", default=None)
@click.option("--agent-id", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def worktree_status(
    ctx: click.Context,
    definition_path: str,
    worktree_id: Optional[str],
    agent_id: Optional[str],
    as_json: bool,
) -> None:
    """Show git status summaries for active worktrees."""
    session_root, sync_root, definition = resolve_acl_roots(ctx, definition_path)
    service = WorktreeService(session_root, sync_root=sync_root, definition_path=definition)
    result = raise_if_error(service.status(worktree_id=worktree_id, agent_id=agent_id))
    if as_json:
        emit_json(result)
        return
    if not result.worktrees:
        click.echo("No active worktrees.")
        return
    for row in result.worktrees:
        click.echo(
            f"{row.get('worktree_id')}\t{row.get('path')}\tdirty={row.get('dirty')}\texists={row.get('exists')}",
        )


@worktree_group.command("list")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--repository", default=None)
@click.option("--agent-id", default=None)
@click.option("--status", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def worktree_list(
    ctx: click.Context,
    definition_path: str,
    repository: Optional[str],
    agent_id: Optional[str],
    status: Optional[str],
    as_json: bool,
) -> None:
    """List worktree records."""
    session_root, sync_root, definition = resolve_acl_roots(ctx, definition_path)
    service = WorktreeService(session_root, sync_root=sync_root, definition_path=definition)
    result = raise_if_error(
        service.list(repository=repository, agent_id=agent_id, status=status),
    )
    if as_json:
        emit_json(result)
        return
    if not result.worktrees:
        click.echo("No worktrees.")
        return
    for row in result.worktrees:
        click.echo(
            f"{row.worktree_id}\t{row.agent_id}\t{row.repository}\t{row.branch}\t{row.status}\t{row.path}",
        )


@worktree_group.command("manifest")
@click.argument("agent_id")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def worktree_manifest(
    ctx: click.Context,
    agent_id: str,
    definition_path: str,
    as_json: bool,
) -> None:
    """Show the agent execution manifest written on worktree create."""
    _ = as_json
    session_root, sync_root, definition = resolve_acl_roots(ctx, definition_path)
    service = WorktreeService(session_root, sync_root=sync_root, definition_path=definition)
    result = raise_if_error(service.manifest(agent_id))
    emit_json(result)

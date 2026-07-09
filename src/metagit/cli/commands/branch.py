#!/usr/bin/env python
"""CLI for ACL branch allocation (RFC-0007)."""

from __future__ import annotations

from typing import Optional

import click

from metagit.cli.commands.acl_common import emit_json, raise_if_error, resolve_acl_roots
from metagit.core.coordination.branch_service import BranchService
from metagit.core.coordination.lease_service import LeaseService
from metagit.core.coordination.worktree_service import WorktreeService


@click.group(name="branch")
@click.pass_context
def branch_group(ctx: click.Context) -> None:
    """Manage agent/* branch allocations (ACL)."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@branch_group.command("allocate")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--repository", required=True, help="project/repo")
@click.option("--agent-id", required=True)
@click.option("--task-id", required=True)
@click.option("--description", default=None, help="Optional short branch suffix")
@click.option("--name", "branch_name", default=None, help="Explicit agent/* branch name")
@click.option("--base", default=None, help="Base ref/commit for the new branch")
@click.option("--integration-branch", default=None)
@click.option("--no-git", is_flag=True, help="Record allocation without creating a git branch")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def branch_allocate(
    ctx: click.Context,
    definition_path: str,
    repository: str,
    agent_id: str,
    task_id: str,
    description: Optional[str],
    branch_name: Optional[str],
    base: Optional[str],
    integration_branch: Optional[str],
    no_git: bool,
    as_json: bool,
) -> None:
    """Allocate a unique agent/* branch."""
    roots = resolve_acl_roots(ctx, definition_path)
    session_root, sync_root, definition = roots.session_root, roots.sync_root, roots.definition_path
    service = BranchService(
        session_root,
        sync_root=sync_root,
        definition_path=definition,
    )
    result = raise_if_error(
        service.allocate(
            repository=repository,
            agent_id=agent_id,
            task_id=task_id,
            description=description,
            branch_name=branch_name,
            base=base,
            integration_branch=integration_branch,
            create_git_branch=not no_git,
        ),
    )
    if as_json:
        emit_json(result)
        return
    click.echo(f"{result.branch_id}\t{result.name}\t{result.repository}\t{result.status}")


@branch_group.command("list")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--repository", default=None)
@click.option("--status", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def branch_list(
    ctx: click.Context,
    definition_path: str,
    repository: Optional[str],
    status: Optional[str],
    as_json: bool,
) -> None:
    """List branch allocations."""
    roots = resolve_acl_roots(ctx, definition_path)
    session_root, sync_root, definition = roots.session_root, roots.sync_root, roots.definition_path
    service = BranchService(session_root, sync_root=sync_root, definition_path=definition)
    result = raise_if_error(service.list(repository=repository, status=status))
    if as_json:
        emit_json(result)
        return
    if not result.branches:
        click.echo("No branch allocations.")
        return
    for row in result.branches:
        click.echo(
            f"{row.branch_id}\t{row.name}\t{row.repository}\t{row.agent_id}\t{row.status}",
        )


@branch_group.command("release")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--branch-id", default=None)
@click.option("--name", default=None)
@click.option("--repository", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def branch_release(
    ctx: click.Context,
    definition_path: str,
    branch_id: Optional[str],
    name: Optional[str],
    repository: Optional[str],
    as_json: bool,
) -> None:
    """Mark a branch allocation as released."""
    roots = resolve_acl_roots(ctx, definition_path)
    session_root, sync_root, definition = roots.session_root, roots.sync_root, roots.definition_path
    service = BranchService(session_root, sync_root=sync_root, definition_path=definition)
    result = raise_if_error(
        service.release(branch_id=branch_id, name=name, repository=repository),
    )
    if as_json:
        emit_json(result)
        return
    click.echo(f"released\t{result.name}\t{result.repository}")


@branch_group.command("archive")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--branch-id", default=None)
@click.option("--name", default=None)
@click.option("--repository", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def branch_archive(
    ctx: click.Context,
    definition_path: str,
    branch_id: Optional[str],
    name: Optional[str],
    repository: Optional[str],
    as_json: bool,
) -> None:
    """Archive a branch allocation record."""
    roots = resolve_acl_roots(ctx, definition_path)
    session_root, sync_root, definition = roots.session_root, roots.sync_root, roots.definition_path
    service = BranchService(session_root, sync_root=sync_root, definition_path=definition)
    result = raise_if_error(
        service.archive(branch_id=branch_id, name=name, repository=repository),
    )
    if as_json:
        emit_json(result)
        return
    click.echo(f"archived\t{result.name}\t{result.repository}")


@branch_group.command("cleanup")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--no-delete-git", is_flag=True, help="Keep local git branches")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def branch_cleanup(
    ctx: click.Context,
    definition_path: str,
    no_delete_git: bool,
    as_json: bool,
) -> None:
    """Delete released/archived branches with no active lease or worktree."""
    roots = resolve_acl_roots(ctx, definition_path)
    session_root, sync_root, definition = roots.session_root, roots.sync_root, roots.definition_path
    events = None
    branch_service = BranchService(
        session_root,
        sync_root=sync_root,
        definition_path=definition,
    )
    lease_service = LeaseService(
        session_root,
        sync_root=sync_root,
        definition_path=definition,
        branch_service=branch_service,
    )
    worktree_service = WorktreeService(
        session_root,
        sync_root=sync_root,
        definition_path=definition,
        lease_service=lease_service,
    )
    lease_keys = raise_if_error(lease_service.active_branch_keys())
    worktree_keys = raise_if_error(worktree_service.active_branch_keys())
    cleaned = raise_if_error(
        branch_service.cleanup(
            delete_git_branches=not no_delete_git,
            active_lease_branches=lease_keys,
            active_worktree_branches=worktree_keys,
        ),
    )
    _ = events
    if as_json:
        emit_json({"ok": True, "cleaned": [row.model_dump(mode="json") for row in cleaned]})
        return
    click.echo(f"cleaned {len(cleaned)} branch allocation(s)")

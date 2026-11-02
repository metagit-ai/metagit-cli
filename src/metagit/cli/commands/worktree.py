#!/usr/bin/env python
"""CLI for ACL worktree management (RFC-0007)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from metagit.cli.commands.acl_common import emit_json, raise_if_error, resolve_acl_roots
from metagit.core.coordination.worktree_service import WorktreeService
from metagit.core.workspace.worktree_discover import (
    default_pr_lookup,
    discover_worktrees,
    gc_merged_worktrees,
)


def _workspace_path(ctx: click.Context) -> str | None:
    """Workspace path from the loaded app config, including ``METAGIT_WORKSPACE_PATH``."""
    config = ctx.obj.get("config") if isinstance(ctx.obj, dict) else None
    workspace = getattr(config, "workspace", None)
    path = getattr(workspace, "path", None)
    return str(path) if path else None


@click.group(name="worktree")
@click.pass_context
def worktree_group(ctx: click.Context) -> None:
    """Manage isolated agent git worktrees."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@worktree_group.command("create")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--repository", required=True, help="project/repo, or . / self for the definition repo")
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
    roots = resolve_acl_roots(ctx, definition_path)
    session_root, sync_root, definition = roots.session_root, roots.sync_root, roots.definition_path
    service = WorktreeService(
        session_root,
        sync_root=sync_root,
        definition_path=definition,
        worktrees_path=roots.worktrees_path,
        worktree_per_task=roots.coordination.worktree_per_task,
        post_create=list(roots.coordination.worktree.post_create),
    )
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


@worktree_group.command("adopt")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--repository", required=True, help="project/repo, or . / self for the definition repo")
@click.option("--path", "checkout_path", required=True, help="Existing worktree path from git worktree list")
@click.option("--agent-id", required=True)
@click.option("--task-id", required=True)
@click.option("--branch", default=None, help="Expected branch. Detached worktrees are refused.")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def worktree_adopt(
    ctx: click.Context,
    definition_path: str,
    repository: str,
    checkout_path: str,
    agent_id: str,
    task_id: str,
    branch: Optional[str],
    as_json: bool,
) -> None:
    """Register an existing git worktree without creating another checkout."""
    roots = resolve_acl_roots(ctx, definition_path)
    session_root, sync_root, definition = roots.session_root, roots.sync_root, roots.definition_path
    service = WorktreeService(
        session_root,
        sync_root=sync_root,
        definition_path=definition,
        worktrees_path=roots.worktrees_path,
        worktree_per_task=roots.coordination.worktree_per_task,
        post_create=list(roots.coordination.worktree.post_create),
    )
    result = raise_if_error(
        service.adopt(
            repository=repository,
            agent_id=agent_id,
            task_id=task_id,
            path=checkout_path,
            branch=branch,
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
@click.option("--repository", default=None, help="project/repo, or . / self for the definition repo")
@click.option("--task-id", default=None, help="Required when the agent has more than one worktree in the repo")
@click.option("--force", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def worktree_destroy(
    ctx: click.Context,
    definition_path: str,
    worktree_id: Optional[str],
    agent_id: Optional[str],
    repository: Optional[str],
    task_id: Optional[str],
    force: bool,
    as_json: bool,
) -> None:
    """Destroy an agent worktree."""
    roots = resolve_acl_roots(ctx, definition_path)
    session_root, sync_root, definition = roots.session_root, roots.sync_root, roots.definition_path
    service = WorktreeService(
        session_root,
        sync_root=sync_root,
        definition_path=definition,
        worktrees_path=roots.worktrees_path,
        worktree_per_task=roots.coordination.worktree_per_task,
        post_create=list(roots.coordination.worktree.post_create),
    )
    result = raise_if_error(
        service.destroy(
            worktree_id=worktree_id,
            agent_id=agent_id,
            repository=repository,
            task_id=task_id,
            force=force,
        ),
    )
    if as_json:
        emit_json(result)
        return
    click.echo(f"destroyed\t{result.worktree_id}\t{result.path}")


@worktree_group.command("gc")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--force", is_flag=True, help="Remove checkouts that still have unsaved or unpushed work")
@click.option("--merged", is_flag=True, help="Remove clean discovered worktrees whose pull request merged or closed")
@click.option("--dry-run", is_flag=True, help="Report what would be destroyed or skipped")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def worktree_gc(
    ctx: click.Context,
    definition_path: str,
    force: bool,
    merged: bool,
    dry_run: bool,
    as_json: bool,
) -> None:
    """Garbage-collect worktrees with expired leases or missing paths."""
    if merged:
        try:
            result = gc_merged_worktrees(
                Path(definition_path),
                dry_run=dry_run,
                pr_lookup=default_pr_lookup,
                workspace_path=_workspace_path(ctx),
            )
        except Exception as exc:
            raise click.ClickException(str(exc).splitlines()[0]) from exc
        if as_json:
            emit_json(result)
            return
        verb = "would remove" if dry_run else "removed"
        click.echo(f"gc {verb} {len(result['remove'])} worktree(s); skipped {len(result['skipped'])}")
        for row in result["remove"]:
            click.echo(row["path"])
        return
    roots = resolve_acl_roots(ctx, definition_path)
    session_root, sync_root, definition = roots.session_root, roots.sync_root, roots.definition_path
    service = WorktreeService(
        session_root,
        sync_root=sync_root,
        definition_path=definition,
        worktrees_path=roots.worktrees_path,
        worktree_per_task=roots.coordination.worktree_per_task,
        post_create=list(roots.coordination.worktree.post_create),
    )
    result = raise_if_error(service.gc(force=force, dry_run=dry_run))
    if as_json:
        emit_json(result)
        return
    verb = "would destroy" if dry_run else "destroyed"
    click.echo(f"gc {verb} {len(result.destroyed)} worktree(s); skipped {len(result.skipped)}")
    for row in result.skipped:
        click.echo(row.message)


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
    roots = resolve_acl_roots(ctx, definition_path)
    session_root, sync_root, definition = roots.session_root, roots.sync_root, roots.definition_path
    service = WorktreeService(
        session_root,
        sync_root=sync_root,
        definition_path=definition,
        worktrees_path=roots.worktrees_path,
        worktree_per_task=roots.coordination.worktree_per_task,
        post_create=list(roots.coordination.worktree.post_create),
    )
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
@click.option("--discover", is_flag=True, help="Walk synced repositories and list every git worktree")
@click.option("--pr", "include_pr", is_flag=True, help="Include pull request state when a forge token is set")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def worktree_list(
    ctx: click.Context,
    definition_path: str,
    repository: Optional[str],
    agent_id: Optional[str],
    status: Optional[str],
    discover: bool,
    include_pr: bool,
    as_json: bool,
) -> None:
    """List worktree records."""
    if discover:
        try:
            records = discover_worktrees(
                Path(definition_path),
                pr_lookup=default_pr_lookup if include_pr else None,
                include_pr=include_pr,
                workspace_path=_workspace_path(ctx),
            )
        except Exception as exc:
            raise click.ClickException(str(exc).splitlines()[0]) from exc
        for record in records:
            record.pop("checkout", None)
        if as_json:
            emit_json({"worktrees": records})
            return
        if not records:
            click.echo("No worktrees.")
            return
        for record in records:
            state = "dirty" if record["dirty"] else "clean"
            ahead = record["ahead"] if record["ahead"] is not None else "-"
            click.echo(f"{record['repo']}\t{record['branch']}\t{state}\tahead={ahead}\t{record['path']}")
        return
    roots = resolve_acl_roots(ctx, definition_path)
    session_root, sync_root, definition = roots.session_root, roots.sync_root, roots.definition_path
    service = WorktreeService(
        session_root,
        sync_root=sync_root,
        definition_path=definition,
        worktrees_path=roots.worktrees_path,
        worktree_per_task=roots.coordination.worktree_per_task,
        post_create=list(roots.coordination.worktree.post_create),
    )
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
    roots = resolve_acl_roots(ctx, definition_path)
    session_root, sync_root, definition = roots.session_root, roots.sync_root, roots.definition_path
    service = WorktreeService(
        session_root,
        sync_root=sync_root,
        definition_path=definition,
        worktrees_path=roots.worktrees_path,
        worktree_per_task=roots.coordination.worktree_per_task,
        post_create=list(roots.coordination.worktree.post_create),
    )
    result = raise_if_error(service.manifest(agent_id))
    emit_json(result)

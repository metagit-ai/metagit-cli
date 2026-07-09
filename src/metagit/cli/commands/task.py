#!/usr/bin/env python
"""CLI for Task Graph & Intent Engine (RFC-0008)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click

from metagit.cli.commands.acl_common import emit_json, raise_if_error, resolve_acl_roots
from metagit.core.taskgraph.service import TaskGraphService


@click.group(name="task")
@click.pass_context
def task_group(ctx: click.Context) -> None:
    """Manage task graphs and intent nodes (RFC-0008)."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def _service(ctx: click.Context, definition_path: str) -> TaskGraphService:
    roots = resolve_acl_roots(ctx, definition_path)
    return TaskGraphService(roots.session_root)


@task_group.command("create")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--title", required=True)
@click.option("--goal", required=True)
@click.option("--acceptance", multiple=True, help="Acceptance criterion (repeatable)")
@click.option("--objective-id", default=None)
@click.option("--handoff-id", default=None)
@click.option("--project", default=None)
@click.option("--repo", "repos", multiple=True)
@click.option("--graph-id", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def task_create(
    ctx: click.Context,
    definition_path: str,
    title: str,
    goal: str,
    acceptance: tuple[str, ...],
    objective_id: Optional[str],
    handoff_id: Optional[str],
    project: Optional[str],
    repos: tuple[str, ...],
    graph_id: Optional[str],
    as_json: bool,
) -> None:
    """Create an empty task graph with a root intent."""
    service = _service(ctx, definition_path)
    result = raise_if_error(
        service.create(
            title=title,
            goal=goal,
            acceptance=list(acceptance),
            objective_id=objective_id,
            handoff_id=handoff_id,
            project=project,
            repos=list(repos),
            graph_id=graph_id,
        ),
    )
    if as_json:
        emit_json(result)
        return
    click.echo(f"{result.graph_id}\t{result.title}\t{result.status}")


@task_group.command("expand")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--graph-id", required=True)
@click.option(
    "--from-outline",
    "outline_path",
    default=None,
    type=click.Path(exists=False, dir_okay=False),
    help="Path to outline file; omit to read STDIN",
)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def task_expand(
    ctx: click.Context,
    definition_path: str,
    graph_id: str,
    outline_path: Optional[str],
    as_json: bool,
) -> None:
    """Expand a graph from an indented outline or JSON list."""
    text = Path(outline_path).read_text(encoding="utf-8") if outline_path else sys.stdin.read()
    service = _service(ctx, definition_path)
    result = raise_if_error(service.expand(graph_id, text))
    if as_json:
        emit_json(result)
        return
    click.echo(f"{result.graph_id}\tnodes={len(result.nodes)}")


@task_group.command("list")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--graph-id", default=None)
@click.option("--status", default=None, help="Filter nodes by status")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def task_list(
    ctx: click.Context,
    definition_path: str,
    graph_id: Optional[str],
    status: Optional[str],
    as_json: bool,
) -> None:
    """List graphs or nodes."""
    service = _service(ctx, definition_path)
    if graph_id or status:
        nodes = raise_if_error(service.list_nodes(graph_id=graph_id, status=status))  # type: ignore[arg-type]
        if as_json:
            emit_json({"nodes": [n.model_dump(mode="json") for n in nodes]})
            return
        for node in nodes:
            click.echo(f"{node.graph_id}\t{node.node_id}\t{node.status}\t{node.title}")
        return
    graphs = raise_if_error(service.list_graphs())
    if as_json:
        emit_json({"graphs": [g.model_dump(mode="json") for g in graphs]})
        return
    for graph in graphs:
        click.echo(f"{graph.graph_id}\t{graph.status}\t{len(graph.nodes)}\t{graph.title}")


@task_group.command("status")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--node-id", required=True)
@click.option("--graph-id", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def task_status(
    ctx: click.Context,
    definition_path: str,
    node_id: str,
    graph_id: Optional[str],
    as_json: bool,
) -> None:
    """Show one node."""
    service = _service(ctx, definition_path)
    result = raise_if_error(service.status(node_id, graph_id=graph_id))
    if as_json:
        emit_json(result)
        return
    click.echo(f"{result.graph_id}\t{result.node_id}\t{result.status}\t{result.title}")


@task_group.command("ready")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--graph-id", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def task_ready(
    ctx: click.Context,
    definition_path: str,
    graph_id: Optional[str],
    as_json: bool,
) -> None:
    """List nodes whose dependencies are satisfied."""
    service = _service(ctx, definition_path)
    result = raise_if_error(service.ready(graph_id))
    if as_json:
        emit_json({"nodes": [n.model_dump(mode="json") for n in result]})
        return
    for node in result:
        click.echo(f"{node.graph_id}\t{node.node_id}\t{node.title}")


@task_group.command("block")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--node-id", required=True)
@click.option("--reason", required=True)
@click.option("--graph-id", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def task_block(
    ctx: click.Context,
    definition_path: str,
    node_id: str,
    reason: str,
    graph_id: Optional[str],
    as_json: bool,
) -> None:
    """Mark a node blocked."""
    service = _service(ctx, definition_path)
    result = raise_if_error(service.block(node_id, reason, graph_id=graph_id))
    if as_json:
        emit_json(result)
        return
    click.echo(f"blocked\t{result.node_id}\t{reason}")


@task_group.command("complete")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--node-id", required=True)
@click.option("--graph-id", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def task_complete(
    ctx: click.Context,
    definition_path: str,
    node_id: str,
    graph_id: Optional[str],
    as_json: bool,
) -> None:
    """Mark a node completed and unlock dependents."""
    service = _service(ctx, definition_path)
    result = raise_if_error(service.complete(node_id, graph_id=graph_id))
    if as_json:
        emit_json(result)
        return
    click.echo(f"completed\t{result.node_id}")


@task_group.command("start")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--node-id", required=True)
@click.option("--graph-id", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def task_start(
    ctx: click.Context,
    definition_path: str,
    node_id: str,
    graph_id: Optional[str],
    as_json: bool,
) -> None:
    """Mark a node running (without scheduler)."""
    service = _service(ctx, definition_path)
    result = raise_if_error(service.start(node_id, graph_id=graph_id))
    if as_json:
        emit_json(result)
        return
    click.echo(f"running\t{result.node_id}")


@task_group.command("bind-acl")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--node-id", required=True)
@click.option("--agent-id", required=True)
@click.option("--graph-id", default=None)
@click.option("--branch", default=None)
@click.option("--lease-id", default=None)
@click.option("--worktree-id", default=None)
@click.option("--pattern", default=None, help="Claim pattern hint")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def task_bind_acl(
    ctx: click.Context,
    definition_path: str,
    node_id: str,
    agent_id: str,
    graph_id: Optional[str],
    branch: Optional[str],
    lease_id: Optional[str],
    worktree_id: Optional[str],
    pattern: Optional[str],
    as_json: bool,
) -> None:
    """Store ACL command hints on a node (does not run git/ACL)."""
    service = _service(ctx, definition_path)
    result = raise_if_error(
        service.bind_acl(
            node_id,
            agent_id=agent_id,
            graph_id=graph_id,
            branch=branch,
            lease_id=lease_id,
            worktree_id=worktree_id,
            pattern=pattern,
        ),
    )
    if as_json:
        emit_json(result)
        return
    click.echo(f"bound\t{result.node_id}\tcommands={len(result.acl.acl_commands if result.acl else [])}")


__all__ = ["task_group"]

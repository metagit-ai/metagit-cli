#!/usr/bin/env python
"""CLI for Distributed Agent Scheduler (RFC-0012)."""

from __future__ import annotations

import json
from typing import Optional

import click

from metagit.cli.commands.acl_common import emit_json, raise_if_error, resolve_acl_roots
from metagit.core.scheduler.service import SchedulerService


@click.group(name="schedule")
@click.pass_context
def schedule_group(ctx: click.Context) -> None:
    """Score ready tasks and emit schedule decisions (RFC-0012)."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def _service(ctx: click.Context, definition_path: str) -> SchedulerService:
    roots = resolve_acl_roots(ctx, definition_path)
    return SchedulerService(roots.session_root)


@schedule_group.group("policy")
@click.pass_context
def schedule_policy(ctx: click.Context) -> None:
    """Show or update the local schedule policy."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@schedule_policy.command("show")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def policy_show(ctx: click.Context, definition_path: str, as_json: bool) -> None:
    """Show the workspace schedule policy."""
    service = _service(ctx, definition_path)
    policy = raise_if_error(service.policy_show())
    if as_json:
        emit_json(policy)
        return
    click.echo(
        f"priority={policy.weights.priority} affinity={policy.weights.affinity} "
        f"cost={policy.weights.cost} fairness={policy.weights.fairness} "
        f"merge_threshold={policy.merge_queue_threshold} "
        f"skip_on_pressure={policy.skip_on_merge_pressure}"
    )


@schedule_policy.command("set")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--priority", type=float, default=None)
@click.option("--affinity", type=float, default=None)
@click.option("--cost", type=float, default=None)
@click.option("--fairness", type=float, default=None)
@click.option("--merge-queue-threshold", type=int, default=None)
@click.option("--merge-pressure-penalty", type=float, default=None)
@click.option("--skip-on-merge-pressure/--no-skip-on-merge-pressure", default=None)
@click.option("--graph-id", default=None, help="Optional graph override target")
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def policy_set(
    ctx: click.Context,
    definition_path: str,
    priority: Optional[float],
    affinity: Optional[float],
    cost: Optional[float],
    fairness: Optional[float],
    merge_queue_threshold: Optional[int],
    merge_pressure_penalty: Optional[float],
    skip_on_merge_pressure: Optional[bool],
    graph_id: Optional[str],
    as_json: bool,
) -> None:
    """Update schedule policy weights and merge-pressure settings."""
    service = _service(ctx, definition_path)
    weights = {
        key: value
        for key, value in {
            "priority": priority,
            "affinity": affinity,
            "cost": cost,
            "fairness": fairness,
        }.items()
        if value is not None
    }
    graph_weights = weights if graph_id else None
    policy = raise_if_error(
        service.policy_set(
            weights=None if graph_id else (weights or None),
            merge_queue_threshold=merge_queue_threshold,
            merge_pressure_penalty=merge_pressure_penalty,
            skip_on_merge_pressure=skip_on_merge_pressure,
            graph_id=graph_id,
            graph_weights=graph_weights,
        )
    )
    if as_json:
        emit_json(policy)
        return
    click.echo("policy updated")


@schedule_group.command("next")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--graph-id", default=None)
@click.option("--limit", default=1, show_default=True, type=int)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def schedule_next(
    ctx: click.Context,
    definition_path: str,
    graph_id: Optional[str],
    limit: int,
    as_json: bool,
) -> None:
    """Return the next schedule decision(s) for ready task nodes."""
    service = _service(ctx, definition_path)
    decisions = raise_if_error(service.next(graph_id, limit=limit))
    if as_json:
        click.echo(json.dumps([row.model_dump(mode="json") for row in decisions], indent=2))
        return
    if not decisions:
        click.echo("No ready nodes.")
        return
    for row in decisions:
        flag = "skipped" if row.skipped else "next"
        click.echo(f"{flag}\t{row.node_id}\t{row.score}\t{row.graph_id}")


@schedule_group.command("status")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--recent", default=10, show_default=True, type=int)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def schedule_status(
    ctx: click.Context,
    definition_path: str,
    recent: int,
    as_json: bool,
) -> None:
    """Show scheduler policy, ready count, and recent decisions."""
    service = _service(ctx, definition_path)
    status = raise_if_error(service.status(recent=recent))
    if as_json:
        emit_json(status)
        return
    click.echo(f"ready={status.ready_count} recent={len(status.recent_decisions)}")
    if status.merge_pressure:
        click.echo("merge_pressure=" + ",".join(f"{k}:{v}" for k, v in status.merge_pressure.items()))

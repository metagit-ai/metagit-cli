#!/usr/bin/env python
"""CLI for mutation policy evaluation (RFC-0022 MVP)."""

from __future__ import annotations

import click

from metagit.cli.json_output import emit_json
from metagit.core.policy.engine import MutationPolicy, evaluate_action

_ACTIONS: tuple[str, ...] = (
    "sync",
    "merge_integrate",
    "claim_declare",
    "claim_release",
    "catalog_edit",
    "remote_state_write",
    "acl_bind",
    "aos_recover",
    "run_open",
)


@click.group(name="policy", invoke_without_command=True)
@click.pass_context
def policy_group(ctx: click.Context) -> None:
    """Evaluate declarative mutation policy."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@policy_group.command("eval")
@click.option(
    "--action",
    required=True,
    type=click.Choice(list(_ACTIONS), case_sensitive=True),
)
@click.option("--json", "as_json", is_flag=True)
def policy_eval(action: str, as_json: bool) -> None:
    """Evaluate whether an action class is allowed (report-only)."""
    decision = evaluate_action(action, MutationPolicy())  # type: ignore[arg-type]
    if as_json:
        emit_json(decision.model_dump(mode="json"))
        return
    click.echo(f"{decision.action}\t{decision.effect}\t{decision.reason}")

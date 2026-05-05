#!/usr/bin/env python
"""
MCP command group for Metagit CLI.
"""

from typing import Optional

import click

from metagit.core.mcp.runtime import MetagitMcpRuntime


@click.group()
def mcp() -> None:
    """Metagit MCP server commands."""


@mcp.command("serve")
@click.option("--root", default=None, help="Optional workspace root override.")
@click.option(
    "--status-once",
    is_flag=True,
    default=False,
    help="Print one-shot status and exit (for diagnostics/tests).",
)
@click.pass_context
def serve(ctx: click.Context, root: Optional[str], status_once: bool) -> None:
    """Start MCP runtime over stdio."""
    runtime = MetagitMcpRuntime(root=root)
    if status_once:
        snapshot = runtime.status_snapshot()
        click.echo(
            f"mcp_state={snapshot['state']} root={snapshot['root'] or 'none'} tools={snapshot['tools']}"
        )
        return

    logger = ctx.obj.get("logger") if ctx.obj else None
    if logger:
        logger.info("Metagit MCP stdio runtime initialized.")
    runtime.run_stdio()

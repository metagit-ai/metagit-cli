#!/usr/bin/env python
"""
MCP command group for Metagit CLI.
"""

from typing import Optional

import click

from metagit.core.mcp.runtime import MetagitMcpRuntime
from metagit.core.skills import (
    SUPPORTED_TARGETS,
    install_mcp_for_targets,
    resolve_project_install_root,
    resolve_targets,
)


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
        click.echo(f"mcp_state={snapshot['state']} root={snapshot['root'] or 'none'} tools={snapshot['tools']}")
        return

    logger = ctx.obj.get("logger") if ctx.obj else None
    if logger:
        logger.info("Metagit MCP stdio runtime initialized.")
    runtime.run_stdio()


@mcp.command("install")
@click.option(
    "--scope",
    type=click.Choice(["project", "user"]),
    default="user",
    show_default=True,
    help="Install to the git repository root (project) or user-global location.",
)
@click.option(
    "--target",
    "targets",
    multiple=True,
    type=click.Choice(SUPPORTED_TARGETS),
    help="Explicit target to install (repeatable). If omitted, auto-detect targets.",
)
@click.option(
    "--disable-target",
    "disable_targets",
    multiple=True,
    type=click.Choice(SUPPORTED_TARGETS),
    help="Disable one or more auto-detected targets.",
)
@click.option(
    "--server-name",
    default="metagit",
    show_default=True,
    help="MCP server key to write in target config files.",
)
@click.pass_context
def install(
    ctx: click.Context,
    scope: str,
    targets: list[str],
    disable_targets: list[str],
    server_name: str,
) -> None:
    """Install metagit MCP server entry into supported agent configs."""
    logger = ctx.obj["logger"] if ctx.obj else None
    project_root = resolve_project_install_root() if scope == "project" else None
    selected_targets = resolve_targets(
        mode="mcp",
        scope=scope,
        enable_targets=list(targets),
        disable_targets=list(disable_targets),
        project_root=project_root,
    )
    if not selected_targets:
        if logger:
            logger.warning("No targets selected. Use --target to choose targets explicitly.")
        else:
            click.echo("No targets selected. Use --target to choose targets explicitly.")
        return
    results = install_mcp_for_targets(
        targets=selected_targets,
        scope=scope,
        server_name=server_name,
        project_root=project_root,
    )
    for result in results:
        if logger:
            logger.success(f"[{result.target}] {result.details} -> {result.path}")
        else:
            click.echo(f"[{result.target}] {result.details} -> {result.path}")

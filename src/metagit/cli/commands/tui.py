#!/usr/bin/env python
"""Interactive TUI hub for Metagit CLI workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from metagit.core.tui import run_tui


def _detect_manifest(cwd: Path) -> Optional[str]:
    candidate = cwd / ".metagit.yml"
    return str(candidate) if candidate.is_file() else None


@click.command("tui")
@click.option(
    "--manifest",
    "-m",
    "manifest_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to .metagit.yml (default: ./.metagit.yml when present)",
)
@click.option(
    "--wizard",
    is_flag=True,
    default=False,
    help="Open directly on the configuration wizard",
)
@click.pass_context
def tui_cmd(ctx: click.Context, manifest_path: Optional[str], wizard: bool) -> None:
    """
    Launch the Metagit TUI hub.

    Browse common CLI workflows, run commands, and configure metagit.config.yaml.
    """
    logger = ctx.obj["logger"]
    if ctx.obj.get("agent_mode"):
        raise click.UsageError("Interactive TUI is disabled in agent mode")

    app_config_path: str = ctx.obj["config_path"]
    cwd = Path.cwd()
    manifest = manifest_path or _detect_manifest(cwd)
    logger.info("Starting Metagit TUI")
    run_tui(
        app_config_path=app_config_path,
        manifest_path=manifest,
        cwd=str(cwd),
        start_wizard=wizard,
    )

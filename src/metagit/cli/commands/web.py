#!/usr/bin/env python
"""Local web UI command group."""

from __future__ import annotations

import webbrowser
from pathlib import Path

import click

from metagit.core.web.server import build_web_server


@click.group()
def web() -> None:
    """Local web UI commands."""


@web.command("serve")
@click.option(
    "--root",
    default=".",
    show_default=True,
    help="Directory containing `.metagit.yml`.",
)
@click.option(
    "--appconfig",
    default=None,
    help="App config path override.",
)
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8787, type=int, show_default=True)
@click.option("--open/--no-open", default=False, help="Open the UI in a browser.")
@click.option(
    "--status-once",
    is_flag=True,
    default=False,
    help="Bind once, print ready line with resolved port, and exit.",
)
@click.pass_context
def serve(
    ctx: click.Context,
    root: str,
    appconfig: str | None,
    host: str,
    port: int,
    open: bool,
    status_once: bool,
) -> None:
    """Serve the metagit web UI and workspace API on localhost."""
    root_abs = str(Path(root).resolve())
    appconfig_path = appconfig
    if appconfig_path is None:
        if ctx.obj is None:
            raise click.ClickException(
                "Missing app config; pass --appconfig or run via metagit CLI."
            )
        appconfig_path = str(ctx.obj["config_path"])
    server = build_web_server(
        root=root_abs,
        appconfig_path=appconfig_path,
        host=host,
        port=port,
    )
    bound_port = server.server_address[1]
    url = f"http://{host}:{bound_port}/"
    if status_once:
        click.echo(f"web_state=ready host={host} port={bound_port} url={url}")
        server.server_close()
        return
    try:
        click.echo(f"Serving metagit web UI on {url} (workspace root {root_abs})")
        if open:
            webbrowser.open(url)
        server.serve_forever()
    except KeyboardInterrupt:
        click.echo("Shutting down.")
    finally:
        server.server_close()

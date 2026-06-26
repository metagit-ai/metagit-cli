#!/usr/bin/env python
"""
Local JSON HTTP API command group.
"""

from pathlib import Path

import click

from metagit.core.api.server import build_server


@click.group()
def api() -> None:
    """Local JSON API commands."""


@api.command("serve")
@click.option(
    "--root",
    default=".",
    show_default=True,
    help="Workspace root containing `.metagit.yml`.",
)
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=7878, type=int, show_default=True)
@click.option(
    "--status-once",
    is_flag=True,
    default=False,
    help="Bind once, print ready line with resolved port, and exit.",
)
def serve(root: str, host: str, port: int, status_once: bool) -> None:
    """Serve managed-repo search JSON endpoints on localhost."""
    root_abs = str(Path(root).resolve())
    server = build_server(root=root_abs, host=host, port=port)
    bound_port = server.server_address[1]
    if status_once:
        click.echo(f"api_state=ready host={host} port={bound_port}")
        server.server_close()
        return
    try:
        click.echo(f"Serving metagit API on http://{host}:{bound_port}/ (workspace root {root_abs})")
        server.serve_forever()
    except KeyboardInterrupt:
        click.echo("Shutting down.")
    finally:
        server.server_close()

#!/usr/bin/env python
"""Install or print shell tab-completion scripts for the Metagit CLI."""

from __future__ import annotations

from pathlib import Path

import click

from metagit.cli.shell_completion import (
    SUPPORTED_SHELLS,
    default_install_path,
    format_install_message,
    install_completion_script,
    render_completion_script,
    shell_activation_hint,
    verify_completion_callback,
)


@click.group(name="completion")
def completion_group() -> None:
    """Generate and install shell tab completion for ``metagit``."""


def _root_cli() -> click.Command:
    from metagit.cli.main import cli

    return cli


@completion_group.command("show")
@click.option(
    "--shell",
    "-s",
    type=click.Choice(SUPPORTED_SHELLS, case_sensitive=False),
    required=True,
    help="Target shell (zsh, bash, fish)",
)
def completion_show(shell: str) -> None:
    """Print a completion script to stdout."""
    click.echo(render_completion_script(_root_cli(), shell_name=shell))


@completion_group.command("install")
@click.option(
    "--shell",
    "-s",
    type=click.Choice(SUPPORTED_SHELLS, case_sensitive=False),
    required=True,
    help="Target shell (zsh, bash, fish)",
)
@click.option(
    "--path",
    "destination",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="Write the completion script to this file (default: OS convention)",
)
@click.option(
    "--stdout",
    is_flag=True,
    default=False,
    help="Print eval/source instructions instead of writing a file",
)
def completion_install(
    shell: str,
    destination: Path | None,
    stdout: bool,
) -> None:
    """Install a user-level completion script or print activation instructions."""
    script = render_completion_script(_root_cli(), shell_name=shell)
    if stdout:
        click.echo(shell_activation_hint(shell))
        return

    target = destination or default_install_path(shell)
    written = install_completion_script(script, shell_name=shell, destination=target)
    ok, detail = verify_completion_callback()
    click.echo(format_install_message(shell, written))
    if ok:
        click.echo(f"Completion callback verified via: {detail}")
    else:
        click.echo(
            f"Note: completion script written, but callback check failed: {detail}",
            err=True,
        )


@completion_group.command("doctor")
def completion_doctor() -> None:
    """Verify that the installed ``metagit`` binary supports completion callbacks."""
    ok, detail = verify_completion_callback()
    if ok:
        click.echo(f"OK: completion callback works ({detail})")
        return
    raise click.ClickException(detail)

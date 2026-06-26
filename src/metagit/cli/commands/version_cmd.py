#!/usr/bin/env python
"""Version and release-check commands for agents and humans."""

from __future__ import annotations

import click

from metagit import __version__
from metagit.cli.json_output import emit_json
from metagit.core.release.release_check_service import ReleaseCheckService
from metagit.core.release.upgrade_service import VersionUpgradeService
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger


@click.group(name="version", invoke_without_command=True)
@click.pass_context
def version_group(ctx: click.Context) -> None:
    """Show installed Metagit version or check for updates."""
    if ctx.invoked_subcommand is not None:
        return
    logger = ctx.obj.get("logger") if ctx.obj else None
    if logger is None:
        logger = UnifiedLogger(LoggerConfig())
    logger.config_element(name="version", value=__version__, console=True)


@version_group.command("check")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print structured JSON for agents",
)
@click.option(
    "--no-notes",
    "no_notes",
    is_flag=True,
    default=False,
    help="Omit release notes body from the response",
)
@click.pass_context
def version_check(
    ctx: click.Context,
    as_json: bool,
    no_notes: bool,
) -> None:
    """Compare installed Metagit against the latest GitHub release and PyPI."""
    _ = ctx
    service = ReleaseCheckService()
    result = service.check(include_notes=not no_notes)
    if as_json:
        emit_json(result)
        return

    click.echo(f"installed: {result.installed_version}")
    if result.latest_release is not None:
        latest = result.latest_release
        published = latest.published_at.date().isoformat() if latest.published_at is not None else "unknown date"
        click.echo(f"latest:    {latest.version} ({published})")
        if latest.html_url:
            click.echo(f"release:   {latest.html_url}")
    elif result.pypi_version is not None:
        click.echo(f"latest:    {result.pypi_version} (PyPI)")
    else:
        click.echo("latest:    unavailable")

    if result.pypi_version is not None and (
        result.latest_release is None or result.pypi_version != result.latest_release.version
    ):
        click.echo(f"pypi:      {result.pypi_version}")

    click.echo("update available: " + ("yes" if result.update_available else "no"))
    if result.update_available:
        click.echo(f"upgrade:   {result.install_command}")

    if not no_notes and result.latest_release and result.latest_release.body:
        click.echo("")
        click.echo("release notes:")
        click.echo(result.latest_release.body)

    for error in result.fetch_errors:
        click.echo(f"warning: {error}", err=True)


@version_group.command("upgrade")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print structured JSON for agents",
)
@click.option(
    "--apply",
    "apply",
    is_flag=True,
    default=False,
    help="Execute the upgrade (default is dry-run)",
)
@click.pass_context
def version_upgrade(ctx: click.Context, as_json: bool, apply: bool) -> None:
    """Upgrade Metagit when a newer release is published on PyPI."""
    _ = ctx
    result = VersionUpgradeService().upgrade(apply=apply)
    if as_json:
        emit_json(result)
        if not result.ok:
            raise SystemExit(1)
        return

    click.echo(f"installed: {result.check.installed_version}")
    click.echo(f"install method: {result.install_method}")
    if not result.ok:
        click.echo(result.message or "Upgrade not available.", err=True)
        if result.stderr:
            click.echo(result.stderr, err=True)
        raise SystemExit(1)

    if result.skipped:
        click.echo(result.message or "Already on the latest published release.")
        return

    if result.command:
        click.echo(f"command: {result.command}")

    if result.dry_run:
        click.echo(result.message or "Dry-run only. Re-run with --apply to upgrade.")
        return

    click.echo(result.message or "Upgrade completed.")
    if result.stdout:
        click.echo(result.stdout)

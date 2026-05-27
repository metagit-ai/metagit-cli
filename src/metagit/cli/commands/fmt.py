#!/usr/bin/env python
"""Format metagit and appconfig YAML files."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from metagit.core.config.format_service import ConfigFormatService, FormatFileResult


def _format_targets(
    *,
    metagit_path: str | None,
    appconfig_path: str | None,
    minimal: bool,
) -> list[FormatFileResult | Exception]:
    service = ConfigFormatService()
    results: list[FormatFileResult | Exception] = []
    if metagit_path is not None:
        results.append(service.format_metagit(metagit_path, minimal=minimal))
    if appconfig_path is not None:
        results.append(service.format_appconfig(appconfig_path, minimal=minimal))
    return results


def _emit_results(
    results: list[FormatFileResult],
    *,
    check: bool,
    stdout: bool,
    logger,
) -> int:
    exit_code = 0
    for result in results:
        label = result.target
        if check:
            if result.changed:
                logger.warning(f"{label}: would reformat {result.path}")
                exit_code = 1
            else:
                logger.success(f"{label}: already formatted ({result.path})")
            continue
        if stdout:
            click.echo(result.formatted, nl=False)
            continue
        if not result.changed:
            logger.success(f"{label}: already formatted ({result.path})")
            continue
        Path(result.path).write_text(result.formatted, encoding="utf-8")
        logger.success(f"{label}: formatted {result.path}")
    return exit_code


@click.command("fmt")
@click.option(
    "--target",
    "-t",
    "targets",
    type=click.Choice(["metagit", "appconfig", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Which configuration file(s) to format",
)
@click.option(
    "--metagit-path",
    default=".metagit.yml",
    show_default=True,
    help="Path to .metagit.yml when formatting the manifest",
)
@click.option(
    "--appconfig-path",
    default=None,
    help="Path to metagit.config.yaml (default: global --config from CLI context)",
)
@click.option(
    "--minimal",
    is_flag=True,
    default=False,
    help="Omit fields equal to schema defaults",
)
@click.option(
    "--check",
    is_flag=True,
    default=False,
    help="Exit 1 when a file would change (no writes)",
)
@click.option(
    "--stdout",
    is_flag=True,
    default=False,
    help="Print formatted YAML to stdout instead of writing files",
)
@click.pass_context
def fmt_cmd(
    ctx: click.Context,
    targets: str,
    metagit_path: str,
    appconfig_path: str | None,
    minimal: bool,
    check: bool,
    stdout: bool,
) -> None:
    """
    Format .metagit.yml and/or metagit.config.yaml with schema field order and clean YAML.

    Re-serializes through the Pydantic models so keys like ``name`` appear first in
    project/repo list entries and long descriptions use readable literal blocks.
    """
    logger = ctx.obj["logger"]
    selected = targets.strip().lower()
    format_metagit = selected in {"metagit", "all"}
    format_appconfig = selected in {"appconfig", "all"}

    resolved_metagit = metagit_path if format_metagit else None
    resolved_appconfig: str | None = None
    if format_appconfig:
        resolved_appconfig = appconfig_path or ctx.obj["config_path"]

    if stdout and selected == "all":
        raise click.ClickException("--stdout requires --target metagit or appconfig")

    if resolved_metagit and not Path(resolved_metagit).is_file():
        logger.warning(f"Skipping missing metagit manifest: {resolved_metagit}")
        resolved_metagit = None
    if resolved_appconfig and not Path(resolved_appconfig).is_file():
        logger.warning(f"Skipping missing appconfig file: {resolved_appconfig}")
        resolved_appconfig = None

    if resolved_metagit is None and resolved_appconfig is None:
        raise click.ClickException("No configuration files found to format")

    pending = _format_targets(
        metagit_path=resolved_metagit,
        appconfig_path=resolved_appconfig,
        minimal=minimal,
    )

    formatted: list[FormatFileResult] = []
    for item in pending:
        if isinstance(item, Exception):
            logger.error(f"Failed to format config: {item}")
            ctx.abort()
        formatted.append(item)

    code = _emit_results(formatted, check=check, stdout=stdout, logger=logger)
    if code:
        sys.exit(code)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This is the entry point for the command-line interface (CLI) application.

It can be used as a handy facility for running the task from a command line.

.. note::

    To learn more about Click visit the
    `project website <http://click.pocoo.org/5/>`_.  There is also a very
    helpful `tutorial video <https://www.youtube.com/watch?v=kNke39OZ2k0>`_.

    To learn more about running Luigi, visit the Luigi project's
    `Read-The-Docs <http://luigi.readthedocs.io/en/stable/>`_ page.

.. currentmodule:: metagit_detect.cli
.. moduleauthor:: Zachary Loeber <zloeber@gmail.com>
"""

from pathlib import Path

import click

from metagit import DEFAULT_CONFIG, __version__
from metagit.cli.commands.appconfig import appconfig
from metagit.cli.commands.config import config
from metagit.cli.commands.detect import detect
from metagit.cli.commands.init import init
from metagit.cli.commands.project import project
from metagit.cli.commands.record import record
from metagit.cli.commands.workspace import workspace
from metagit.core.appconfig import load_config
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger

CONTEXT_SETTINGS: dict = {
    "help_option_names": ["-h", "--help"],
    "max_content_width": 120,
}


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.version_option(__version__)
@click.option(
    "--config",
    "-c",
    default="metagit.config.yaml",
    help="Path to the configuration file",
)
@click.option("--debug/--no-debug", default=False, help="Enable or disable debug mode")
@click.option(
    "--verbose/--no-verbose", default=False, help="Enable or disable verbose output"
)
@click.pass_context
def cli(ctx: click.Context, config: str, debug: bool, verbose: bool) -> None:
    """
    Metagit CLI: A multi-purpose CLI tool with YAML configuration.
    """
    # If no subcommand is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return
    log_level: str = "INFO"
    minimal_console: bool = True
    if verbose:
        log_level = "INFO"
        minimal_console = False
    if debug:
        log_level = "DEBUG"
        minimal_console = False

    try:
        logger: UnifiedLogger = UnifiedLogger(
            LoggerConfig(log_level=log_level, minimal_console=minimal_console)
        )

        if not Path(config).exists():
            logger.debug(
                f"Config file '{config}' not found, using default: {DEFAULT_CONFIG}"
            )
            config = DEFAULT_CONFIG
        cfg = load_config(config)
        if isinstance(cfg, Exception):
            logger.error(f"Error loading config: {cfg}")
            ctx.abort()

        # Store the configuration and logger in the context
        ctx.obj = {
            "config_path": config,
            "config": cfg,
            "logger": logger,
            "verbose": verbose,
            "debug": debug,
        }
    except Exception as e:
        logger = UnifiedLogger(LoggerConfig())
        logger.error(f"An unexpected error occurred in CLI setup: {e}")
        ctx.abort()


@cli.command()
@click.pass_context
def info(ctx: click.Context) -> None:
    """
    Display the current configuration.
    """
    logger = ctx.obj.get("logger") or UnifiedLogger(LoggerConfig())

    logger.config_element(name="version", value=__version__, console=True)
    logger.config_element(
        name="config_path", value=ctx.obj["config_path"], console=True
    )
    logger.config_element(name="debug", value=ctx.obj["debug"], console=True)
    logger.config_element(name="verbose", value=ctx.obj["verbose"], console=True)


@cli.command()
@click.pass_context
def version(ctx: click.Context) -> None:
    """Get the application version."""
    logger = ctx.obj.get("logger") or UnifiedLogger(LoggerConfig())
    logger.config_element(name="version", value=__version__, console=True)


cli.add_command(detect)
cli.add_command(appconfig)
cli.add_command(project)
cli.add_command(workspace)
cli.add_command(config)
cli.add_command(record)
cli.add_command(init)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()

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
from metagit.cli.commands.agent import agent
from metagit.cli.commands.api import api
from metagit.cli.commands.appconfig import appconfig
from metagit.cli.commands.completion_cmd import completion_group
from metagit.cli.commands.config import config
from metagit.cli.commands.context import context
from metagit.cli.commands.detect import detect
from metagit.cli.commands.fmt import fmt_cmd
from metagit.cli.commands.gitnexus import gitnexus
from metagit.cli.commands.init import init
from metagit.cli.commands.mcp import mcp
from metagit.cli.commands.project import project
from metagit.cli.commands.prompt import prompt
from metagit.cli.commands.record import record
from metagit.cli.commands.search import search
from metagit.cli.commands.skills import skills
from metagit.cli.commands.tui import tui_cmd
from metagit.cli.commands.version_cmd import version_group
from metagit.cli.commands.web import web
from metagit.cli.commands.workspace import workspace
from metagit.core.appconfig import load_config, resolve_agent_mode
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
@click.option("--verbose/--no-verbose", default=False, help="Enable or disable verbose output")
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
        logger: UnifiedLogger = UnifiedLogger(LoggerConfig(log_level=log_level, minimal_console=minimal_console))

        if not Path(config).exists():
            logger.debug(f"Config file '{config}' not found, using default: {DEFAULT_CONFIG}")
            config = DEFAULT_CONFIG
        cfg = load_config(config)
        if isinstance(cfg, Exception):
            logger.error(f"Error loading config: {cfg}")
            ctx.abort()

        # Store the configuration and logger in the context
        ctx.obj = {
            "config_path": config,
            "config": cfg,
            "agent_mode": resolve_agent_mode(cfg),
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
    logger.config_element(name="config_path", value=ctx.obj["config_path"], console=True)
    logger.config_element(name="debug", value=ctx.obj["debug"], console=True)
    logger.config_element(name="verbose", value=ctx.obj["verbose"], console=True)


cli.add_command(version_group)
cli.add_command(detect)
cli.add_command(appconfig)
cli.add_command(project)
cli.add_command(workspace)
cli.add_command(config)
cli.add_command(record)
cli.add_command(skills)
cli.add_command(agent)
cli.add_command(init)
cli.add_command(mcp)
cli.add_command(gitnexus)
cli.add_command(api)
cli.add_command(web)
cli.add_command(search)
cli.add_command(search, name="find")
cli.add_command(prompt)
cli.add_command(context)
cli.add_command(completion_group)
cli.add_command(fmt_cmd, name="fmt")
cli.add_command(fmt_cmd, name="format")
cli.add_command(tui_cmd, name="tui")


def main() -> None:
    """Console entry point with a stable completion env var on all platforms."""
    from metagit.cli.shell_completion import _COMPLETION_ENV

    cli.main(
        prog_name="metagit",
        complete_var=_COMPLETION_ENV,
        standalone_mode=True,
    )


if __name__ == "__main__":
    main()

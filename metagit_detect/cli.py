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

import os
import sys
from pathlib import Path

import click

from metagit_detect import DEFAULT_CONFIG, __version__
from metagit_detect.commands.appconfig import appconfig
from metagit_detect.commands.detect import detect
from metagit_detect.config import Config, load_config
from utils.logging import LOG_LEVELS, LoggerConfig, UnifiedLogger

CONTEXT_SETTINGS: dict = dict(help_option_names=["-h", "--help"], max_content_width=120)


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.version_option(__version__)
@click.option(
    "--config", default="metagit.config.yaml", help="Path to the configuration file"
)
@click.option("--debug/--no-debug", default=None, help="Enable or disable debug mode")
@click.option(
    "--verbose/--no-verbose", default=None, help="Enable or disable verbose output"
)
@click.option(
    "--strict/--no-strict", default=None, help="Enable or disable strict mode"
)
@click.option("--override", default=None, help="Override configuration value")
@click.option("--llm-provider", default=None, help="LLM provider")
@click.option("--llm-provider-model", default=None, help="LLM provider model")
@click.option("--workspace-path", default=None, help="Workspace path")
@click.pass_context
def cli(
    ctx,
    config,
    debug,
    verbose,
    strict,
    override,
    llm_provider,
    llm_provider_model,
    workspace_path,
):
    """
    Metagit CLI: A multi-purpose CLI tool with YAML configuration.
    """
    logger: UnifiedLogger = UnifiedLogger(LoggerConfig())
    if verbose:
        logger.set_level(level=LOG_LEVELS[3])
        logger.config_element(name="verbose", value="ENABLED", console=True)
    if debug:
        logger.set_level(level=LOG_LEVELS[0])
        logger.config_element(name="debug", value="ENABLED", console=True)
    if not Path(config).exists():
        logger.debug(
            f"Config file '{config}' not found, using default: {DEFAULT_CONFIG}"
        )
        config = DEFAULT_CONFIG
    cfg = load_config(config)
    # Apply command-line overrides if provided
    overrides = {}
    if debug is not None:
        overrides["global_config"] = overrides.get("global_config", {})
        overrides["global_config"]["debug"] = debug
    if verbose is not None:
        overrides["global_config"] = overrides.get("global_config", {})
        overrides["global_config"]["verbose"] = verbose
    if strict is not None:
        overrides["global_config"] = overrides.get("global_config", {})
        overrides["global_config"]["strict"] = strict
    if override is not None:
        overrides["global_config"] = overrides.get("global_config", {})
        overrides["global_config"]["override"] = override
    if llm_provider is not None:
        overrides["llm"] = overrides.get("llm", {})
        overrides["llm"]["provider"] = llm_provider
    if llm_provider_model is not None:
        overrides["llm"] = overrides.get("llm", {})
        overrides["llm"]["provider_model"] = llm_provider_model
    if workspace_path is not None:
        overrides["workspace"] = overrides.get("workspace", {})
        overrides["workspace"]["path"] = workspace_path

    # Update configuration with overrides
    if overrides:
        config_dict = cfg.model_dump(by_alias=True)
        for section, values in overrides.items():
            if section in config_dict:
                config_dict[section].update(values)
            else:
                config_dict[section] = values
        cfg = Config(**config_dict)

    # Store the configuration and logger in the context
    ctx.obj = {"config_path": config, "config": cfg, "logger": logger}


@cli.command()
@click.pass_context
def info(ctx):
    """
    Display the current configuration.
    """
    cfg = ctx.obj["config"]
    click.echo("Metagit CLI:")
    click.echo(f"Version: {cfg.version}")
    click.echo(f"Config Path: {cfg.config_path}")
    click.echo(f"Debug: {cfg.global_config.debug}")
    click.echo(f"Verbose: {cfg.global_config.verbose}")
    click.echo(f"Override: {cfg.global_config.override}")


@cli.command()
@click.pass_context
def version(ctx):
    """Get the library version."""
    ctx.obj["logger"].config_element(name="version", value=__version__, console=True)


cli.add_command(detect)
cli.add_command(appconfig)


if __name__ == "__main__":
    cli()

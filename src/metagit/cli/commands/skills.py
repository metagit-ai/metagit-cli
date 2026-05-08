#!/usr/bin/env python
"""
Skills command group for bundled skill management.
"""

from typing import List

import click

from metagit.core.skills import (
    SUPPORTED_TARGETS,
    install_skills_for_targets,
    list_bundled_skills,
    resolve_targets,
    skill_markdown,
)


@click.group(name="skills", invoke_without_command=True)
@click.pass_context
def skills(ctx: click.Context) -> None:
    """Bundled skill management commands."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return


@skills.command("list")
@click.pass_context
def skills_list(ctx: click.Context) -> None:
    """List bundled skills available for install."""
    logger = ctx.obj["logger"]
    bundled = list_bundled_skills()
    if not bundled:
        logger.warning("No bundled skills found in package data.")
        return
    logger.info("Bundled skills:")
    for skill_name in bundled:
        logger.echo(f"- {skill_name}")


@skills.command("show")
@click.argument("skill_name", required=False)
@click.pass_context
def skills_show(ctx: click.Context, skill_name: str | None) -> None:
    """Show a bundled skill document."""
    logger = ctx.obj["logger"]
    if not skill_name:
        skill_names = list_bundled_skills()
        if not skill_names:
            logger.warning("No bundled skills found in package data.")
            return
        logger.info("Available skills:")
        for item in skill_names:
            logger.echo(f"- {item}")
        logger.info("Use `metagit skills show <name>` to print SKILL.md content.")
        return
    content = skill_markdown(skill_name)
    if not content:
        logger.error(f"Skill '{skill_name}' not found.")
        ctx.abort()
    logger.echo(content)


@skills.command("install")
@click.option(
    "--scope",
    type=click.Choice(["project", "user"]),
    default="user",
    show_default=True,
    help="Install to local project config or user-global location.",
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
@click.pass_context
def skills_install(
    ctx: click.Context,
    scope: str,
    targets: List[str],
    disable_targets: List[str],
) -> None:
    """Install bundled skills into supported agent targets."""
    logger = ctx.obj["logger"]
    selected_targets = resolve_targets(
        mode="skills",
        scope=scope,
        enable_targets=list(targets),
        disable_targets=list(disable_targets),
    )
    if not selected_targets:
        logger.warning(
            "No targets selected. Use --target to choose targets explicitly."
        )
        return
    results = install_skills_for_targets(targets=selected_targets, scope=scope)
    for result in results:
        if result.applied:
            logger.success(f"[{result.target}] {result.details} -> {result.path}")
        else:
            logger.warning(f"[{result.target}] {result.details} -> {result.path}")

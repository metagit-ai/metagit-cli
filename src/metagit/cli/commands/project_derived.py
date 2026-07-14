#!/usr/bin/env python
"""CLI for derived workspace projects (surgical subsets in one umbrella)."""

from __future__ import annotations

import sys
from typing import Optional

import click

from metagit.cli.json_output import emit_json
from metagit.core.config.models import MetagitConfig
from metagit.core.utils.logging import UnifiedLogger
from metagit.core.workspace.derived_project_service import DerivedProjectService


def _exit_on_derived(result: object, *, as_json: bool) -> None:
    """Emit derived mutation result and exit non-zero on failure."""
    if as_json:
        emit_json(result)  # type: ignore[arg-type]
    else:
        ok = bool(getattr(result, "ok", True))
        error = getattr(result, "error", None)
        if not ok and error is not None:
            click.echo(f"Error ({error.kind}): {error.message}", err=True)
        elif ok:
            operation = getattr(result, "operation", "updated")
            project_name = getattr(result, "project_name", "")
            repos = getattr(result, "repo_names", []) or []
            repo_bit = f" repos={','.join(repos)}" if repos else ""
            click.echo(f"derived {operation}: {project_name}{repo_bit}")
    if not bool(getattr(result, "ok", True)):
        raise SystemExit(1)


@click.group(name="derived")
def derived() -> None:
    """Create and maintain derived surgical workspace projects."""


@derived.command("create")
@click.option("--name", "-n", required=True, help="Name for the new derived project")
@click.option(
    "--from",
    "selections",
    multiple=True,
    required=True,
    help="Source selection as project/repo (repeatable)",
)
@click.option("--description", default=None, help="Optional project description")
@click.option(
    "--agent-instructions",
    default=None,
    help="Optional agent instructions for the derived project",
)
@click.option(
    "--no-dedupe",
    is_flag=True,
    default=False,
    help="Do not enable per-project dedupe (fails if identities already exist)",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def derived_create(
    ctx: click.Context,
    name: str,
    selections: tuple[str, ...],
    description: Optional[str],
    agent_instructions: Optional[str],
    no_dedupe: bool,
    as_json: bool,
) -> None:
    """Create a derived project from frozen project/repo selections."""
    local_config: MetagitConfig = ctx.obj["local_config"]
    config_path: str = ctx.obj["config_path"]
    result = DerivedProjectService().create(
        local_config,
        config_path,
        name=name,
        selections=list(selections),
        description=description,
        agent_instructions=agent_instructions,
        enable_dedupe=not no_dedupe,
    )
    _exit_on_derived(result, as_json=as_json)


@derived.command("refresh")
@click.option(
    "--project",
    "-p",
    "derived_project",
    default=None,
    help="Derived project name (defaults to active -p on project group)",
)
@click.option(
    "--repo",
    "-r",
    "repos",
    multiple=True,
    help="Limit refresh to these derived repo names (repeatable)",
)
@click.option("--force", is_flag=True, default=False, help="Allow refresh on protected projects")
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def derived_refresh(
    ctx: click.Context,
    derived_project: Optional[str],
    repos: tuple[str, ...],
    force: bool,
    as_json: bool,
) -> None:
    """Re-pull identity fields from source without changing membership."""
    logger: UnifiedLogger = ctx.obj["logger"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    config_path: str = ctx.obj["config_path"]
    project_name = derived_project or ctx.obj.get("project")
    if not project_name:
        logger.error("Provide --project or use metagit project -p <name> derived refresh")
        sys.exit(1)
    result = DerivedProjectService().refresh(
        local_config,
        config_path,
        project_name=project_name,
        repo_names=list(repos) if repos else None,
        force=force,
    )
    _exit_on_derived(result, as_json=as_json)


@derived.command("include")
@click.option(
    "--project",
    "-p",
    "derived_project",
    default=None,
    help="Derived project name (defaults to active -p on project group)",
)
@click.option(
    "--from",
    "selection",
    required=True,
    help="Source selection as project/repo",
)
@click.option("--force", is_flag=True, default=False, help="Allow include on protected projects")
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def derived_include(
    ctx: click.Context,
    derived_project: Optional[str],
    selection: str,
    force: bool,
    as_json: bool,
) -> None:
    """Add one source repo to a derived project's frozen membership."""
    logger: UnifiedLogger = ctx.obj["logger"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    config_path: str = ctx.obj["config_path"]
    project_name = derived_project or ctx.obj.get("project")
    if not project_name:
        logger.error("Provide --project or use metagit project -p <name> derived include")
        sys.exit(1)
    result = DerivedProjectService().include(
        local_config,
        config_path,
        project_name=project_name,
        selection=selection,
        force=force,
    )
    _exit_on_derived(result, as_json=as_json)


@derived.command("exclude")
@click.option(
    "--project",
    "-p",
    "derived_project",
    default=None,
    help="Derived project name (defaults to active -p on project group)",
)
@click.option("--repo", "-r", required=True, help="Derived repo name to remove")
@click.option("--force", is_flag=True, default=False, help="Allow exclude on protected repos")
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def derived_exclude(
    ctx: click.Context,
    derived_project: Optional[str],
    repo: str,
    force: bool,
    as_json: bool,
) -> None:
    """Remove one repo from a derived project's frozen membership."""
    logger: UnifiedLogger = ctx.obj["logger"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    config_path: str = ctx.obj["config_path"]
    project_name = derived_project or ctx.obj.get("project")
    if not project_name:
        logger.error("Provide --project or use metagit project -p <name> derived exclude")
        sys.exit(1)
    result = DerivedProjectService().exclude(
        local_config,
        config_path,
        project_name=project_name,
        repo_name=repo,
        force=force,
    )
    _exit_on_derived(result, as_json=as_json)

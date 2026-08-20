#!/usr/bin/env python
"""CLI for durable repository CI topology (ProjectPath.ci)."""

from __future__ import annotations

import json
from typing import Optional

import click

from metagit.cli.shell_completion import complete_repos
from metagit.core.config.models import MetagitConfig
from metagit.core.project.ci_models import CiProvider, CiTargetStatus
from metagit.core.project.ci_target_service import CiTargetService
from metagit.core.utils.logging import UnifiedLogger


@click.group(name="ci")
@click.pass_context
def repo_ci(ctx: click.Context) -> None:
    """Show, detect, and set repository CI topology bindings."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@repo_ci.command("show")
@click.option(
    "--repo",
    "repo_name",
    required=True,
    shell_complete=complete_repos,
    help="Repository name within the active project",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit JSON")
@click.pass_context
def ci_show(ctx: click.Context, repo_name: str, as_json: bool) -> None:
    """Show durable CI topology for a managed repository."""
    logger: UnifiedLogger = ctx.obj["logger"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    project_name: str = ctx.obj["project"]
    config_path: str = ctx.obj["config_path"]
    if not project_name:
        raise click.UsageError("Active project required (-p/--project)")
    result = CiTargetService().show(
        config=local_config,
        project_name=project_name,
        repo_name=repo_name,
        config_path=config_path,
    )
    if as_json:
        click.echo(json.dumps(result, indent=2))
    elif not result.get("ok"):
        logger.error(str(result.get("error")))
    else:
        ci = result.get("ci")
        if ci is None:
            logger.info(f"{project_name}/{repo_name}: no ci binding")
        else:
            logger.info(f"{project_name}/{repo_name}: {json.dumps(ci)}")
    if not result.get("ok"):
        ctx.abort()


@repo_ci.command("detect")
@click.option(
    "--repo",
    "repo_name",
    required=True,
    shell_complete=complete_repos,
    help="Repository name within the active project",
)
@click.option("--apply/--no-apply", default=False, show_default=True, help="Write detected ci into .metagit.yml")
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Re-detect even when status is declared/overridden",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit JSON")
@click.pass_context
def ci_detect(
    ctx: click.Context,
    repo_name: str,
    apply: bool,
    force: bool,
    as_json: bool,
) -> None:
    """Detect CI topology from remote URL and on-disk CI config files."""
    logger: UnifiedLogger = ctx.obj["logger"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    project_name: str = ctx.obj["project"]
    config_path: str = ctx.obj["config_path"]
    if not project_name:
        raise click.UsageError("Active project required (-p/--project)")
    result = CiTargetService().detect(
        config=local_config,
        project_name=project_name,
        repo_name=repo_name,
        config_path=config_path,
        apply=apply,
        force=force,
    )
    if as_json:
        click.echo(json.dumps(result, indent=2))
    elif not result.get("ok"):
        logger.error(str(result.get("error")))
    else:
        action = "applied" if result.get("applied") else "detected"
        logger.info(f"{action}: {json.dumps(result.get('ci'))}")
    if not result.get("ok"):
        ctx.abort()


@repo_ci.command("set")
@click.option(
    "--repo",
    "repo_name",
    required=True,
    shell_complete=complete_repos,
    help="Repository name within the active project",
)
@click.option(
    "--provider",
    type=click.Choice([item.value for item in CiProvider]),
    required=True,
)
@click.option("--config-path", "config_paths", multiple=True, help="Repo-relative CI file (repeatable)")
@click.option("--organization", default=None, help="Azure DevOps organization")
@click.option("--ado-project", "ado_project", default=None, help="Azure DevOps project")
@click.option("--repository", default=None, help="Azure DevOps repository name")
@click.option("--definition-id", "definition_ids", multiple=True, help="ADO definition id (repeatable)")
@click.option("--owner", default=None, help="GitHub owner")
@click.option("--name", "repo_short_name", default=None, help="GitHub repo name")
@click.option("--project-path", default=None, help="GitLab project path")
@click.option("--host", default=None, help="CI host override")
@click.option(
    "--status",
    type=click.Choice([CiTargetStatus.DECLARED.value, CiTargetStatus.OVERRIDDEN.value]),
    default=CiTargetStatus.DECLARED.value,
    show_default=True,
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit JSON")
@click.pass_context
def ci_set(
    ctx: click.Context,
    repo_name: str,
    provider: str,
    config_paths: tuple[str, ...],
    organization: Optional[str],
    ado_project: Optional[str],
    repository: Optional[str],
    definition_ids: tuple[str, ...],
    owner: Optional[str],
    repo_short_name: Optional[str],
    project_path: Optional[str],
    host: Optional[str],
    status: str,
    as_json: bool,
) -> None:
    """Declare or override durable CI topology for a managed repository."""
    logger: UnifiedLogger = ctx.obj["logger"]
    local_config: MetagitConfig = ctx.obj["local_config"]
    project_name: str = ctx.obj["project"]
    config_path: str = ctx.obj["config_path"]
    if not project_name:
        raise click.UsageError("Active project required (-p/--project)")
    result = CiTargetService().set_target(
        config=local_config,
        project_name=project_name,
        repo_name=repo_name,
        config_path=config_path,
        provider=provider,
        config_paths=list(config_paths),
        organization=organization,
        project=ado_project,
        repository=repository,
        definition_ids=list(definition_ids),
        owner=owner,
        name=repo_short_name,
        project_path=project_path,
        host=host,
        status=status,
    )
    if as_json:
        click.echo(json.dumps(result, indent=2))
    elif not result.get("ok"):
        logger.error(str(result.get("error")))
    else:
        logger.success(f"Set ci for {project_name}/{repo_name}")
    if not result.get("ok"):
        ctx.abort()

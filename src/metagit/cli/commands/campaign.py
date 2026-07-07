#!/usr/bin/env python
"""Native workspace campaign commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from metagit.core.appconfig import load_config as load_appconfig
from metagit.core.campaign.service import CampaignService
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.workspace.root_resolver import resolve_definition_root, resolve_session_root, resolve_sync_root


def _parse_tag_filters(tag_values: tuple[str, ...]) -> dict[str, str] | None:
    if not tag_values:
        return None
    parsed: dict[str, str] = {}
    for item in tag_values:
        if "=" not in item:
            raise click.ClickException(f"Invalid --tag (expected key=value): {item!r}")
        key, value = item.split("=", 1)
        parsed[key] = value
    return parsed


def _emit_json(payload: object) -> None:
    click.echo(json.dumps(payload, indent=2, sort_keys=False))


def _campaign_service(
    definition_path: str,
    *,
    config_path: Optional[str] = None,
    campaigns_path: Optional[str] = None,
) -> tuple[CampaignService, Path]:
    manager = MetagitConfigManager(config_path=definition_path)
    config = manager.load_config()
    if isinstance(config, Exception):
        raise click.ClickException(str(config))
    definition_root = Path(resolve_definition_root(definition_path))
    workspace_root = definition_root
    resolved_campaigns_path = campaigns_path
    if config_path:
        appconfig = load_appconfig(config_path)
        if not isinstance(appconfig, Exception) and appconfig.workspace:
            if appconfig.workspace.path:
                workspace_root = Path(
                    resolve_sync_root(str(definition_root), appconfig.workspace.path),
                )
            if resolved_campaigns_path is None:
                resolved_campaigns_path = appconfig.workspace.campaigns_path
    service = CampaignService(
        config=config,
        definition_root=definition_root,
        workspace_root=workspace_root,
        campaigns_path=resolved_campaigns_path,
    )
    return service, definition_root


@click.group(name="campaign", invoke_without_command=True)
@click.pass_context
def campaign(ctx: click.Context) -> None:
    """Manage cross-project campaign overlays (default directory: ``_campaigns/``)."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return


@campaign.command("list")
@click.option(
    "--definition",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
    help="Path to the Metagit workspace definition file",
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def campaign_list(ctx: click.Context, definition_path: str, as_json: bool) -> None:
    """List campaigns with rollup counts."""
    _ = ctx
    service, _ = _campaign_service(definition_path, config_path=ctx.obj.get("config_path"))
    result = service.list_campaigns()
    if as_json:
        _emit_json(result.model_dump(mode="json"))
        return
    if not result.campaigns:
        click.echo("No campaigns found.")
        return
    for item in result.campaigns:
        click.echo(
            f"{item.slug}\t{item.status}\t{item.merged_count}/{item.repo_count} merged\t{item.title}",
        )


@campaign.command("status")
@click.option("--slug", required=True, help="Campaign slug.")
@click.option(
    "--definition",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def campaign_status(ctx: click.Context, slug: str, definition_path: str, as_json: bool) -> None:
    """Show detailed campaign status and repo rollup."""
    _ = ctx
    service, _ = _campaign_service(definition_path, config_path=ctx.obj.get("config_path"))
    result = service.status(slug)
    if result is None:
        raise click.ClickException(f"Unknown campaign: {slug!r}")
    if as_json:
        _emit_json(result.model_dump(mode="json"))
        return
    click.echo(f"{result.campaign.title} ({result.campaign.status})")
    if result.campaign.goal:
        click.echo(f"goal: {result.campaign.goal}")
    if result.campaign.reference_impl:
        click.echo(f"reference: {result.campaign.reference_impl}")
    click.echo(
        f"rollup: {result.merged_count} merged, {result.open_mr_count} MRs open, "
        f"{result.blocked_count} blocked, {result.pending_count} pending",
    )
    for repo in result.campaign.repos:
        mr = f" mr={repo.mr}" if repo.mr else ""
        note = f" note={repo.note}" if repo.note else ""
        click.echo(f"  {repo.project}/{repo.repo}\t{repo.status}{mr}{note}")


@campaign.command("new")
@click.option("--slug", required=True, help="Campaign slug (filename stem).")
@click.option("--title", required=True, help="Human-readable campaign title.")
@click.option(
    "--query",
    default=None,
    help="Repository selection query (metagit find syntax). Provide this or --repo.",
)
@click.option(
    "--repo",
    "repo_selectors",
    multiple=True,
    help="Explicit project/repo to include (repeatable). Freezes the repo set (no query drift).",
)
@click.option("--tag", "tag_values", multiple=True, help="Optional tag filter during selection.")
@click.option("--goal", default=None, help="Free-text objective describing what the campaign delivers.")
@click.option("--reference", "reference_impl", default=None, help="Exemplar repo (project/repo) to model changes on.")
@click.option("--objective-id", default=None, help="Optional spine objective id to bind.")
@click.option(
    "--definition",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def campaign_new(
    ctx: click.Context,
    slug: str,
    title: str,
    query: Optional[str],
    repo_selectors: tuple[str, ...],
    tag_values: tuple[str, ...],
    goal: Optional[str],
    reference_impl: Optional[str],
    objective_id: Optional[str],
    definition_path: str,
    as_json: bool,
) -> None:
    """Create a campaign by resolving repos from a query or an explicit --repo list."""
    _ = ctx
    service, _ = _campaign_service(definition_path, config_path=ctx.obj.get("config_path"))
    try:
        document = service.create(
            slug=slug,
            title=title,
            query=query,
            repos=list(repo_selectors) or None,
            tag_filters=_parse_tag_filters(tag_values),
            objective_id=objective_id,
            goal=goal,
            reference_impl=reference_impl,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        _emit_json(document.model_dump(mode="json"))
        return
    click.echo(f"Created campaign {document.slug} with {len(document.repos)} repos.")


@campaign.command("validate")
@click.option(
    "--definition",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.pass_context
def campaign_validate(ctx: click.Context, definition_path: str) -> None:
    """Validate every campaign document and atlas repo references."""
    logger = ctx.obj["logger"]
    service, _ = _campaign_service(definition_path, config_path=ctx.obj.get("config_path"))
    issues = service.validate_all()
    if not issues:
        logger.success("All campaigns validated.")
        return
    for issue in issues:
        logger.error(f"campaign {issue.slug}: {issue.message}")
    raise click.ClickException("Campaign validation failed.")


@campaign.command("set")
@click.option("--slug", required=True, help="Campaign slug.")
@click.option("--repo", required=True, help="Repo selector as project/repo.")
@click.option(
    "--status",
    required=True,
    type=click.Choice(["pending", "routed", "mr-open", "merged", "blocked"]),
)
@click.option("--mr", default=None, help="Merge request URL.")
@click.option("--note", default=None, help="Status note.")
@click.option(
    "--definition",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def campaign_set(
    ctx: click.Context,
    slug: str,
    repo: str,
    status: str,
    mr: Optional[str],
    note: Optional[str],
    definition_path: str,
    as_json: bool,
) -> None:
    """Update one campaign repo entry."""
    _ = ctx
    if "/" not in repo:
        raise click.ClickException("--repo must be project/repo")
    project, repo_name = repo.split("/", 1)
    service, _ = _campaign_service(definition_path, config_path=ctx.obj.get("config_path"))
    try:
        document = service.set_repo_status(
            slug=slug,
            project=project,
            repo=repo_name,
            status=status,  # type: ignore[arg-type]
            mr=mr,
            note=note,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        _emit_json(document.model_dump(mode="json"))
        return
    click.echo(f"Updated {repo} -> {status}")


@campaign.command("expand")
@click.option("--slug", required=True, help="Campaign slug.")
@click.option("--tag", "tag_values", multiple=True, help="Optional tag filter for expansion.")
@click.option("--dry-run", is_flag=True, help="Show objective ids without writing.")
@click.option(
    "--definition",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def campaign_expand(
    ctx: click.Context,
    slug: str,
    tag_values: tuple[str, ...],
    dry_run: bool,
    definition_path: str,
    as_json: bool,
) -> None:
    """Generate one spine objective per matching campaign repo."""
    _ = ctx
    service, definition_root = _campaign_service(
        definition_path,
        config_path=ctx.obj.get("config_path"),
    )
    session_root = Path(resolve_session_root(str(definition_root)))
    try:
        result = service.expand(
            slug=slug,
            session_root=session_root,
            tag_filters=_parse_tag_filters(tag_values),
            dry_run=dry_run,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        _emit_json(result.model_dump(mode="json"))
        return
    verb = "Would create" if dry_run else "Created"
    click.echo(f"{verb} {len(result.objective_ids)} objectives for campaign {slug}.")

#!/usr/bin/env python
"""Native workspace campaign commands."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import click

from metagit.core.appconfig import load_config as load_appconfig
from metagit.core.appconfig.models import AppConfig
from metagit.core.campaign.context import CampaignContextService
from metagit.core.campaign.context_models import (
    CONTEXT_INCLUDE_CHOICES,
    DEFAULT_CONTEXT_INCLUDES,
    CampaignContextResult,
)
from metagit.core.campaign.everroom_service import CampaignEverRoomService, EverRoomSettings
from metagit.core.campaign.models import CampaignDocument
from metagit.core.campaign.service import CampaignService
from metagit.core.campaign.settings import everroom_settings_from_appconfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.context.reduction import (
    DEFAULT_CAMPAIGN_EXPAND_LIMIT,
    DEFAULT_CAMPAIGN_STATUS_REPO_LIMIT,
)
from metagit.core.integrations.everroom.errors import EverRoomError
from metagit.core.workitem.azure_devops import AzureDevOpsBoardClient
from metagit.core.workitem.board_service import CampaignBoardService
from metagit.core.workitem.refs import parse_work_item_ref
from metagit.core.workspace.root_resolver import resolve_definition_root, resolve_session_root, resolve_sync_root


@dataclass
class _CampaignRuntime:
    service: CampaignService
    definition_root: Path
    workspace_root: Path
    config: MetagitConfig
    everroom: EverRoomSettings


def _campaign_create_payload(document: CampaignDocument) -> dict:
    return {
        "ok": True,
        "slug": document.slug,
        "title": document.title,
        "status": document.status,
        "repo_count": len(document.repos),
        "goal": document.goal,
        "reference_impl": document.reference_impl,
        "work_item": document.work_item.model_dump(mode="json") if document.work_item else None,
        "selection": document.selection.model_dump(mode="json"),
    }


def _parse_optional_work_item(
    work_item: Optional[str],
    *,
    url: Optional[str] = None,
    organization: Optional[str] = None,
    project: Optional[str] = None,
    kind: Optional[str] = None,
):
    if not work_item:
        return None
    return parse_work_item_ref(
        work_item,
        url=url,
        organization=organization,
        project=project,
        kind=kind,
    )


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


def _campaign_runtime(
    definition_path: str,
    *,
    config_path: Optional[str] = None,
    campaigns_path: Optional[str] = None,
) -> _CampaignRuntime:
    manager = MetagitConfigManager(config_path=definition_path)
    config = manager.load_config()
    if isinstance(config, Exception):
        raise click.ClickException(str(config))
    definition_root = Path(resolve_definition_root(definition_path))
    workspace_root = definition_root
    resolved_campaigns_path = campaigns_path
    appconfig: Optional[AppConfig] = None
    if config_path:
        loaded = load_appconfig(config_path)
        if not isinstance(loaded, Exception):
            appconfig = loaded
            if appconfig.workspace:
                if appconfig.workspace.path:
                    workspace_root = Path(
                        resolve_sync_root(str(definition_root), appconfig.workspace.path),
                    )
                if resolved_campaigns_path is None:
                    resolved_campaigns_path = appconfig.workspace.campaigns_path
    else:
        loaded = AppConfig.load()
        appconfig = loaded if not isinstance(loaded, Exception) else None
    service = CampaignService(
        config=config,
        definition_root=definition_root,
        workspace_root=workspace_root,
        campaigns_path=resolved_campaigns_path,
    )
    return _CampaignRuntime(
        service=service,
        definition_root=definition_root,
        workspace_root=workspace_root,
        config=config,
        everroom=everroom_settings_from_appconfig(appconfig),
    )


def _campaign_service(
    definition_path: str,
    *,
    config_path: Optional[str] = None,
    campaigns_path: Optional[str] = None,
) -> tuple[CampaignService, Path]:
    runtime = _campaign_runtime(
        definition_path,
        config_path=config_path,
        campaigns_path=campaigns_path,
    )
    return runtime.service, runtime.definition_root


def _everroom_service(runtime: _CampaignRuntime) -> CampaignEverRoomService:
    context_service = CampaignContextService(
        campaign_service=runtime.service,
        config=runtime.config,
        workspace_root=runtime.workspace_root,
        definition_root=runtime.definition_root,
        endpoint=runtime.everroom.endpoint,
        token=runtime.everroom.token,
        timeout_seconds=runtime.everroom.timeout_seconds,
    )
    return CampaignEverRoomService(
        campaign_service=runtime.service,
        context_service=context_service,
        settings=runtime.everroom,
    )


def _raise_everroom(exc: EverRoomError) -> None:
    raise click.ClickException(exc.message) from exc


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
@click.option(
    "--limit",
    type=int,
    default=DEFAULT_CAMPAIGN_STATUS_REPO_LIMIT,
    show_default=True,
    help="Max repo rows to include (JSON and human). Use 0 for counts-only.",
)
@click.option("--offset", type=int, default=0, show_default=True)
@click.option(
    "--repo-status",
    default=None,
    type=click.Choice(["pending", "routed", "mr-open", "merged", "blocked"]),
    help="Filter the paged repo window by status.",
)
@click.option(
    "--include-repos/--no-repos",
    default=True,
    show_default=True,
    help="Include a paged repo window. Counts are always returned.",
)
@click.pass_context
def campaign_status(
    ctx: click.Context,
    slug: str,
    definition_path: str,
    as_json: bool,
    limit: int,
    offset: int,
    repo_status: Optional[str],
    include_repos: bool,
) -> None:
    """Show campaign status with a paged repo window (not the full overlay)."""
    _ = ctx
    service, _ = _campaign_service(definition_path, config_path=ctx.obj.get("config_path"))
    effective_limit = None if limit < 0 else (0 if limit == 0 else limit)
    if effective_limit == 0:
        include_repos = False
        effective_limit = DEFAULT_CAMPAIGN_STATUS_REPO_LIMIT
    result = service.status(
        slug,
        include_repos=include_repos,
        limit=effective_limit,
        offset=offset,
        repo_status=repo_status,
    )
    if result is None:
        raise click.ClickException(f"Unknown campaign: {slug!r}")
    if as_json:
        _emit_json(result.model_dump(mode="json"))
        return
    click.echo(f"{result.title} ({result.status})")
    if result.goal:
        click.echo(f"goal: {result.goal}")
    if result.reference_impl:
        click.echo(f"reference: {result.reference_impl}")
    if result.work_item:
        click.echo(f"work_item: {result.work_item.provider}:{result.work_item.id}")
    click.echo(
        f"rollup: {result.merged_count} merged, {result.open_mr_count} MRs open, "
        f"{result.blocked_count} blocked, {result.pending_count} pending "
        f"({result.repo_count} repos)"
    )
    if result.truncated:
        click.echo(f"repos truncated at offset={result.offset} limit={result.limit}")
    for repo in result.repos:
        mr = f" mr={repo.mr}" if repo.mr else ""
        note = f" note={repo.note}" if repo.note else ""
        work = f" work_item={repo.work_item.provider}:{repo.work_item.id}" if repo.work_item else ""
        click.echo(f"  {repo.project}/{repo.repo}\t{repo.status}{mr}{note}{work}")


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
@click.option("--work-item", default=None, help="Parent board ref (azure_devops:123 or URL).")
@click.option("--work-item-url", default=None, help="Browser URL for the parent work item.")
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
    work_item: Optional[str],
    work_item_url: Optional[str],
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
            work_item=_parse_optional_work_item(work_item, url=work_item_url),
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        _emit_json(_campaign_create_payload(document))
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
@click.option("--work-item", default=None, help="Board ref for this repo (azure_devops:123 or URL).")
@click.option("--work-item-url", default=None, help="Browser URL for the repo work item.")
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
    work_item: Optional[str],
    work_item_url: Optional[str],
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
            work_item=_parse_optional_work_item(work_item, url=work_item_url),
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        updated = next(
            (row for row in document.repos if row.project == project and row.repo == repo_name),
            None,
        )
        _emit_json(
            {
                "ok": True,
                "slug": document.slug,
                "repo": updated.model_dump(mode="json") if updated else None,
            }
        )
        return
    click.echo(f"Updated {repo} -> {status}")


@campaign.command("expand")
@click.option("--slug", required=True, help="Campaign slug.")
@click.option("--tag", "tag_values", multiple=True, help="Optional tag filter for expansion.")
@click.option("--dry-run", is_flag=True, help="Show objective ids without writing.")
@click.option(
    "--limit",
    type=int,
    default=DEFAULT_CAMPAIGN_EXPAND_LIMIT,
    show_default=True,
    help="Max objectives to create this call. Page with --offset.",
)
@click.option("--offset", type=int, default=0, show_default=True)
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
    limit: int,
    offset: int,
    definition_path: str,
    as_json: bool,
) -> None:
    """Generate one spine objective per matching campaign repo (paged)."""
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
            limit=None if limit < 0 else limit,
            offset=offset,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        _emit_json(result.model_dump(mode="json"))
        return
    verb = "Would create" if dry_run else "Created"
    extra = f" (truncated, matched={result.matched_count})" if result.truncated else ""
    click.echo(f"{verb} {len(result.objective_ids)} objectives for campaign {slug}.{extra}")


@campaign.command("board-sync")
@click.option("--slug", required=True, help="Campaign slug.")
@click.option(
    "--provider",
    type=click.Choice(["azure_devops"]),
    default="azure_devops",
    show_default=True,
)
@click.option("--organization", default=None, help="ADO organization (or METAGIT_AZURE_DEVOPS_ORGANIZATION).")
@click.option("--ado-project", "ado_project", default=None, help="ADO project (or METAGIT_AZURE_DEVOPS_PROJECT).")
@click.option("--parent-type", default="Feature", show_default=True)
@click.option("--child-type", default="User Story", show_default=True)
@click.option(
    "--limit",
    type=int,
    default=DEFAULT_CAMPAIGN_EXPAND_LIMIT,
    show_default=True,
    help="Max child work items to create this call.",
)
@click.option("--offset", type=int, default=0, show_default=True)
@click.option("--dry-run", is_flag=True, help="Report what would be created without calling ADO.")
@click.option(
    "--definition",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def campaign_board_sync(
    ctx: click.Context,
    slug: str,
    provider: str,
    organization: Optional[str],
    ado_project: Optional[str],
    parent_type: str,
    child_type: str,
    limit: int,
    offset: int,
    dry_run: bool,
    definition_path: str,
    as_json: bool,
) -> None:
    """Create or refresh Azure DevOps work items for a campaign (paged)."""
    _ = provider
    runtime = _campaign_runtime(definition_path, config_path=ctx.obj.get("config_path"))
    appconfig = load_appconfig(ctx.obj.get("config_path"))
    ado = None if isinstance(appconfig, Exception) else appconfig.providers.azure_devops
    token = (ado.api_token if ado else "") or ""
    org = organization or (ado.organization if ado else "") or ""
    project = ado_project or (ado.project if ado else "") or ""
    base_url = (ado.base_url if ado else "https://dev.azure.com") or "https://dev.azure.com"
    if not dry_run and not token:
        raise click.ClickException(
            "Azure DevOps token required. Set METAGIT_AZURE_DEVOPS_API_TOKEN or AZURE_DEVOPS_EXT_PAT."
        )
    if not org or not project:
        raise click.ClickException("Azure DevOps --organization and --ado-project are required.")
    client = AzureDevOpsBoardClient(
        api_token=token or "dry-run",
        organization=org,
        project=project,
        base_url=base_url,
    )
    service = CampaignBoardService(campaign_service=runtime.service, client=client)
    result = service.sync(
        slug=slug,
        parent_kind=parent_type,
        child_kind=child_type,
        limit=limit,
        offset=offset,
        dry_run=dry_run,
    )
    if as_json:
        _emit_json(result.model_dump(mode="json"))
        if not result.ok:
            raise click.ClickException(result.error or "board sync failed")
        return
    if not result.ok:
        raise click.ClickException(result.error or "board sync failed")
    click.echo(
        f"campaign {result.slug}: created {len(result.created)} work items, "
        f"skipped {result.skipped}, truncated={result.truncated}"
    )


@campaign.command("context")
@click.option("--slug", required=True, help="Campaign slug.")
@click.option(
    "--include",
    "include_values",
    multiple=True,
    type=click.Choice(CONTEXT_INCLUDE_CHOICES),
    help="Context sections to include (repeatable). Default is a concise packet.",
)
@click.option(
    "--definition",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def campaign_context(
    ctx: click.Context,
    slug: str,
    include_values: tuple[str, ...],
    definition_path: str,
    as_json: bool,
) -> None:
    """Assemble provenance-aware campaign context from MetaGit and optional EverRoom."""
    runtime = _campaign_runtime(definition_path, config_path=ctx.obj.get("config_path"))
    service = _everroom_service(runtime)
    include = list(include_values) or list(DEFAULT_CONTEXT_INCLUDES)
    try:
        result = service.context(slug, include=include)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        _emit_json(result.model_dump(mode="json"))
        return
    _print_campaign_context(result)
    for warning in result.warnings:
        click.echo(f"warning: {warning}", err=True)


@campaign.group("everroom")
def campaign_everroom() -> None:
    """Optional EverRoom Room association for a campaign."""


@campaign_everroom.command("status")
@click.option("--slug", required=True, help="Campaign slug.")
@click.option(
    "--definition",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def campaign_everroom_status(
    ctx: click.Context,
    slug: str,
    definition_path: str,
    as_json: bool,
) -> None:
    """Show EverRoom connection and Room association for a campaign."""
    runtime = _campaign_runtime(definition_path, config_path=ctx.obj.get("config_path"))
    service = _everroom_service(runtime)
    try:
        health = service.status(slug)
        campaign = runtime.service.load(slug)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if campaign is None:
        raise click.ClickException(f"Unknown campaign: {slug!r}")
    payload = {
        "campaign": campaign.slug,
        "campaign_status": campaign.status,
        "objective": campaign.goal,
        "metagit": {
            "repositories": len(campaign.repos),
        },
        "everroom": health.model_dump(mode="json"),
    }
    if as_json:
        _emit_json(payload)
        return
    click.echo(f"Campaign: {campaign.slug}")
    click.echo("")
    click.echo("MetaGit")
    click.echo(f"  Status: {campaign.status}")
    click.echo(f"  Repositories: {len(campaign.repos)}")
    click.echo("")
    click.echo("EverRoom")
    click.echo(f"  Status: {health.status.lower()}")
    if health.room_id:
        title = f" ({health.room_title})" if health.room_title else ""
        click.echo(f"  Room: {health.room_id}{title}")
    if health.endpoint:
        click.echo(f"  Endpoint: {health.endpoint}")
    if health.message:
        click.echo(f"  {health.message}")


@campaign_everroom.command("attach")
@click.option("--slug", required=True, help="Campaign slug.")
@click.option("--room", "room_id", required=True, help="EverRoom Room id (not the campaign slug).")
@click.option("--endpoint", default=None, help="Override EverRoom Gateway base URL.")
@click.option(
    "--definition",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def campaign_everroom_attach(
    ctx: click.Context,
    slug: str,
    room_id: str,
    endpoint: Optional[str],
    definition_path: str,
    as_json: bool,
) -> None:
    """Associate an existing EverRoom Room with a campaign."""
    runtime = _campaign_runtime(definition_path, config_path=ctx.obj.get("config_path"))
    service = _everroom_service(runtime)
    try:
        result = service.attach(slug, room_id=room_id, endpoint=endpoint)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    except EverRoomError as exc:
        _raise_everroom(exc)
    if as_json:
        _emit_json(result.model_dump(mode="json"))
        return
    click.echo(f"Attached campaign {result.slug} to EverRoom Room {result.room_id}.")


@campaign_everroom.command("create")
@click.option("--slug", required=True, help="Campaign slug.")
@click.option("--endpoint", default=None, help="Override EverRoom Gateway base URL.")
@click.option(
    "--definition",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def campaign_everroom_create(
    ctx: click.Context,
    slug: str,
    endpoint: Optional[str],
    definition_path: str,
    as_json: bool,
) -> None:
    """Create a derived EverRoom Room from campaign metadata and attach it."""
    runtime = _campaign_runtime(definition_path, config_path=ctx.obj.get("config_path"))
    service = _everroom_service(runtime)
    try:
        result = service.create_room(slug, endpoint=endpoint)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    except EverRoomError as exc:
        _raise_everroom(exc)
    if as_json:
        _emit_json(result.model_dump(mode="json"))
        return
    click.echo(f"Created EverRoom Room {result.room_id} for campaign {result.slug}.")


@campaign_everroom.command("detach")
@click.option("--slug", required=True, help="Campaign slug.")
@click.option(
    "--definition",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def campaign_everroom_detach(
    ctx: click.Context,
    slug: str,
    definition_path: str,
    as_json: bool,
) -> None:
    """Remove the EverRoom association. The remote Room is not deleted."""
    runtime = _campaign_runtime(definition_path, config_path=ctx.obj.get("config_path"))
    service = _everroom_service(runtime)
    try:
        document = service.detach(slug)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        _emit_json({"slug": document.slug, "detached": True, "room_deleted": False})
        return
    click.echo(f"Detached EverRoom from campaign {document.slug}. Room was not deleted.")


@campaign_everroom.command("sync")
@click.option("--slug", required=True, help="Campaign slug.")
@click.option(
    "--definition",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.pass_context
def campaign_everroom_sync(
    ctx: click.Context,
    slug: str,
    definition_path: str,
    as_json: bool,
) -> None:
    """Project MetaGit campaign state into a generated EverRoom document."""
    runtime = _campaign_runtime(definition_path, config_path=ctx.obj.get("config_path"))
    service = _everroom_service(runtime)
    try:
        result = service.sync(slug)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    except EverRoomError as exc:
        _raise_everroom(exc)
    if as_json:
        _emit_json(result.model_dump(mode="json"))
        return
    click.echo(
        f"Synced generated document {result.document_id} (v{result.version}) into Room {result.room_id}.",
    )


def _print_campaign_context(result: CampaignContextResult) -> None:
    packet = result
    click.echo(f"Campaign: {packet.campaign.id}")
    click.echo("")
    click.echo("Objective:")
    click.echo(f"  {packet.campaign.objective or '(none)'}")
    click.echo("")
    click.echo("MetaGit")
    click.echo(f"  Status: {packet.campaign.status}")
    click.echo(f"  Repositories: {packet.metagit.repository_count}")
    click.echo(f"  Components: {packet.metagit.component_count}")
    click.echo(f"  Dependencies: {packet.metagit.relationship_count}")
    click.echo(f"  Dirty repositories: {packet.metagit.dirty_repository_count}")
    click.echo("")
    click.echo("EverRoom")
    click.echo(f"  Status: {packet.everroom.status.lower()}")
    if packet.everroom.room_id:
        title = f" ({packet.everroom.room_title})" if packet.everroom.room_title else ""
        click.echo(f"  Room: {packet.everroom.room_id}{title}")
    click.echo(f"  Evidence sources: {packet.everroom.source_count}")
    click.echo(f"  Decisions: {packet.everroom.decision_count}")
    click.echo(f"  Open questions: {packet.everroom.open_question_count}")
    click.echo(f"  Context documents: {packet.everroom.document_count}")
    if packet.everroom.overview:
        click.echo("")
        click.echo("Context:")
        click.echo(f"  {packet.everroom.overview}")
    if packet.everroom.decisions:
        click.echo("")
        click.echo("Decisions:")
        for decision in packet.everroom.decisions:
            title = decision.get("title") or decision.get("decision_id") or "decision"
            reason = decision.get("reason") or ""
            suffix = f" — {reason}" if reason else ""
            click.echo(f"  - {title}{suffix}")
    if packet.everroom.open_questions:
        click.echo("")
        click.echo("Open questions:")
        for question in packet.everroom.open_questions:
            click.echo(f"  - {question.get('title')}")

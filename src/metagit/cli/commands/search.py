#!/usr/bin/env python
"""
Managed workspace repository search (`.metagit.yml` corpus only).
"""

from pathlib import Path

import click

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.project.search_service import ManagedRepoSearchService


def _parse_tag_filters(tag_values: tuple[str, ...]) -> dict[str, str] | None:
    """Parse repeated `--tag key=value` into a tag filter dict."""
    if not tag_values:
        return None
    parsed: dict[str, str] = {}
    for item in tag_values:
        if "=" not in item:
            raise click.ClickException(f"Invalid --tag (expected key=value): {item!r}")
        key, value = item.split("=", 1)
        parsed[key] = value
    return parsed


@click.command("search")
@click.argument("query")
@click.option(
    "--definition",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
    help="Path to the Metagit workspace definition file",
)
@click.option(
    "--project", default=None, help="Limit to a single workspace project name"
)
@click.option(
    "--exact", is_flag=True, default=False, help="Require exact repository name match"
)
@click.option(
    "--synced-only",
    is_flag=True,
    default=False,
    help="Only include repositories that exist on disk as git checkouts",
)
@click.option(
    "--tag",
    "tag_values",
    multiple=True,
    help="Filter by tag (repeatable), e.g. --tag domain=terraform-module",
)
@click.option(
    "--status",
    "status_values",
    multiple=True,
    help="Filter by repo status (repeatable), e.g. --status synced",
)
@click.option(
    "--sort",
    default="score",
    type=click.Choice(["score", "project", "name"], case_sensitive=False),
    show_default=True,
)
@click.option("--limit", default=10, type=int, show_default=True)
@click.option(
    "--json", "as_json", is_flag=True, default=False, help="Print matches as JSON"
)
@click.option(
    "--path-only",
    is_flag=True,
    default=False,
    help="Resolve to a single local path (errors if ambiguous or not found)",
)
@click.pass_context
def search(
    ctx: click.Context,
    query: str,
    definition_path: str,
    project: str | None,
    exact: bool,
    synced_only: bool,
    tag_values: tuple[str, ...],
    status_values: tuple[str, ...],
    sort: str,
    limit: int,
    as_json: bool,
    path_only: bool,
) -> None:
    """Search managed repositories declared in `.metagit.yml` (alias: `metagit find`)."""
    _ = ctx
    manager = MetagitConfigManager(definition_path)
    config = manager.load_config()
    if isinstance(config, Exception):
        raise click.ClickException(str(config))

    workspace_root = str(Path(definition_path).resolve().parent)
    tag_filters = _parse_tag_filters(tag_values)
    service = ManagedRepoSearchService()
    status_filter = list(status_values) if status_values else None
    result = service.search(
        config=config,
        workspace_root=workspace_root,
        query=query,
        project=project,
        exact=exact,
        synced_only=synced_only,
        tags=tag_filters,
        status=status_filter,
        sort=sort,
        limit=limit,
    )
    if as_json:
        click.echo(result.model_dump_json(indent=2))
        return
    if path_only:
        resolved = service.resolve_one(
            config=config,
            workspace_root=workspace_root,
            query=query,
            project=project,
            exact=exact,
            synced_only=synced_only,
            tags=tag_filters,
            status=status_filter,
            sort=sort,
        )
        if resolved.error:
            raise click.ClickException(resolved.error.message)
        if resolved.match is None:
            raise click.ClickException("No managed repository matched the query.")
        click.echo(resolved.match.status.resolved_path)
        return
    if not result.matches:
        raise click.ClickException(f"No managed repository matched '{query}'.")
    for index, match in enumerate(result.matches, start=1):
        click.echo(f"{index}. project={match.project_name} repo={match.repo_name}")
        click.echo(f"   path={match.status.resolved_path}")
        click.echo(
            "   status="
            f"{match.status.status} exists={match.status.exists} "
            f"git={match.status.is_git_repo} sync={match.status.sync_enabled}"
        )
        click.echo(f"   matched={','.join(match.match_reasons)}")

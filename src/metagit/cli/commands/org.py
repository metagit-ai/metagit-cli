#!/usr/bin/env python
"""Organization index and search commands."""

from __future__ import annotations

from pathlib import Path

import click

from metagit.cli.json_output import emit_json
from metagit.core.appconfig.models import AppConfig
from metagit.core.orgindex.indexer import GitHubOrgIndexer
from metagit.core.orgindex.search import OrgSearchService
from metagit.core.orgindex.store import default_index_home


@click.group(name="org")
@click.pass_context
def org_group(ctx: click.Context) -> None:
    """Index and search GitHub organizations without cloning every repository."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@org_group.group(name="index")
@click.pass_context
def org_index_group(ctx: click.Context) -> None:
    """Build or refresh a disposable organization index."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@org_index_group.command("github")
@click.argument("organization")
@click.option("--refresh", is_flag=True, help="Re-fingerprint repositories whose GitHub pushed_at changed.")
@click.option("--full", is_flag=True, help="Fetch languages, trees, and extra GitHub metadata for every repository.")
@click.option("--json", "as_json", is_flag=True, help="Print a JSON envelope.")
@click.pass_context
def org_index_github(
    ctx: click.Context,
    organization: str,
    refresh: bool,
    full: bool,
    as_json: bool,
) -> None:
    """Index GitHub organization repositories into ~/.metagit/indexes/github/."""
    app_config: AppConfig = ctx.obj["config"]
    indexer = GitHubOrgIndexer(app_config=app_config, index_home=_index_home())
    result = indexer.index(organization, refresh=refresh, full=full)
    if as_json:
        emit_json(result)
    else:
        if not result.ok:
            click.echo(result.error or "organization index failed", err=True)
        else:
            click.echo(f"Indexed {result.indexed} repositories")
            click.echo(f"Updated {result.updated} repositories")
            click.echo(f"Discovered {result.discovered} new repositories")
            click.echo(f"Removed/archived {result.removed} repositories")
            if result.inferred_relationships:
                click.echo(f"Inferred {result.inferred_relationships} similar_to relationships")
    if not result.ok:
        raise SystemExit(1)


@org_group.command("search")
@click.argument("query", required=False, default="")
@click.option("--organization", "--org", default=None, help="Limit search to one indexed GitHub organization.")
@click.option("--language", default=None, help="Primary language filter (csharp, python, …).")
@click.option("--topic", default=None, help="GitHub topic filter.")
@click.option("--has", "has_file", default=None, help="Fingerprint path, filename, or detector tag (Dockerfile, terraform).")
@click.option("--stale-days", type=int, default=None, help="Only repositories not pushed within N days.")
@click.option("--limit", type=int, default=50, show_default=True)
@click.option("--json", "as_json", is_flag=True, help="Print a JSON envelope.")
@click.pass_context
def org_search(
    ctx: click.Context,
    query: str,
    organization: str | None,
    language: str | None,
    topic: str | None,
    has_file: str | None,
    stale_days: int | None,
    limit: int,
    as_json: bool,
) -> None:
    """Search indexed organization repositories. No local checkouts required."""
    _ = ctx
    service = OrgSearchService(index_home=_index_home())
    result = service.search(
        query or None,
        organization=organization,
        language=language,
        topic=topic,
        has=has_file,
        stale_days=stale_days,
        limit=limit,
    )
    if as_json:
        emit_json(result)
    else:
        if not result.ok:
            click.echo(result.error or "organization search failed", err=True)
        elif not result.hits:
            click.echo("No indexed repositories matched.")
        else:
            for hit in result.hits:
                extra = hit.language or ""
                suffix = f" ({extra})" if extra else ""
                click.echo(f"{hit.name}{suffix}")
    if not result.ok:
        raise SystemExit(1)


def _index_home() -> Path:
    return default_index_home()

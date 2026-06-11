#!/usr/bin/env python
"""
Workspace import alias for provider source sync.
"""

from __future__ import annotations

from typing import Optional

import click

from metagit.cli.commands.project_source import source_sync


@click.command("import")
@click.option(
    "--project",
    "-p",
    required=True,
    help="Workspace project name to import into",
)
@click.option(
    "--provider",
    type=click.Choice(["github", "gitlab"]),
    required=True,
    help="Source provider",
)
@click.option("--org", help="GitHub organization")
@click.option("--user", help="GitHub user")
@click.option("--group", help="GitLab group path")
@click.option(
    "--ignore",
    "ignore_patterns",
    multiple=True,
    help="fnmatch denylist on provider full_name (repeatable)",
)
@click.option(
    "--include-pattern",
    "include_patterns",
    multiple=True,
    help="fnmatch allowlist on provider full_name (repeatable)",
)
@click.option(
    "--sync/--no-sync",
    default=False,
    show_default=True,
    help="Clone or update repos after manifest apply",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=True,
    show_default=True,
    help="Print JSON result (default for import alias)",
)
@click.pass_context
def workspace_import(
    ctx: click.Context,
    project: str,
    provider: str,
    org: Optional[str],
    user: Optional[str],
    group: Optional[str],
    ignore_patterns: tuple[str, ...],
    include_patterns: tuple[str, ...],
    sync: bool,
    as_json: bool,
) -> None:
    """Bulk-import repos from a GitHub org/user or GitLab group (additive + ensure)."""
    ctx.obj["project"] = project
    ctx.invoke(
        source_sync,
        provider=provider,
        org=org,
        user=user,
        group=group,
        mode="additive",
        recursive=True,
        include_archived=False,
        include_forks=False,
        path_prefix=None,
        include_patterns=include_patterns,
        ignore_patterns=ignore_patterns,
        name_strategy="namespaced",
        ensure=True,
        refresh_metadata=False,
        no_enrich_topics=False,
        apply=True,
        yes=False,
        sync=sync,
        as_json=as_json,
    )

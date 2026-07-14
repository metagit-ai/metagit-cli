#!/usr/bin/env python
"""CLI for Metagit Atlas commands (RFC-0014)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from metagit.cli.commands.acl_common import emit_json, raise_if_error
from metagit.core.atlas.models import (
    AtlasQueryResult,
    AtlasStatusResult,
    AtlasValidateResult,
)
from metagit.core.atlas.query import AtlasQuery
from metagit.core.atlas.service import AtlasService


@click.group(name="atlas")
@click.pass_context
def atlas_group(ctx: click.Context) -> None:
    """Manage repository-local Metagit Atlas artifacts."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def _resolve_repo_path(path: str) -> Path:
    return Path(path).expanduser().resolve()


def _service(path: str) -> AtlasService:
    return AtlasService(_resolve_repo_path(path))


def _query(path: str) -> AtlasQuery:
    return AtlasQuery(_resolve_repo_path(path))


def _echo_status(result: AtlasStatusResult) -> None:
    freshness = ",".join(f"{key}={value}" for key, value in sorted(result.freshness.items()))
    click.echo(
        f"ok\t{result.repository or '-'}\t"
        f"initialized={result.initialized}\tgenerated={result.generated}" + (f"\t{freshness}" if freshness else ""),
    )


@atlas_group.command("init")
@click.option("--path", "repo_path", default=".", show_default=True)
@click.option("--generate", is_flag=True, help="Run generate after init")
@click.option("--repository", default=None, help="Repository identity for atlas.yaml")
@click.option("--json", "as_json", is_flag=True)
def atlas_init(
    repo_path: str,
    generate: bool,
    repository: Optional[str],
    as_json: bool,
) -> None:
    """Initialize the local Atlas layout."""
    result = raise_if_error(
        _service(repo_path).init(repository=repository, generate=generate),
    )
    assert isinstance(result, AtlasStatusResult)
    if as_json:
        emit_json(result)
        return
    _echo_status(result)


@atlas_group.command("generate")
@click.option("--path", "repo_path", default=".", show_default=True)
@click.option("--json", "as_json", is_flag=True)
def atlas_generate(repo_path: str, as_json: bool) -> None:
    """Generate deterministic Atlas evidence artifacts."""
    result = raise_if_error(_service(repo_path).generate())
    assert isinstance(result, AtlasStatusResult)
    if as_json:
        emit_json(result)
        return
    _echo_status(result)


@atlas_group.command("validate")
@click.option("--path", "repo_path", default=".", show_default=True)
@click.option("--json", "as_json", is_flag=True)
def atlas_validate(repo_path: str, as_json: bool) -> None:
    """Validate Atlas configuration and curated entity references."""
    result = raise_if_error(_service(repo_path).validate())
    assert isinstance(result, AtlasValidateResult)
    if as_json:
        emit_json(result)
    elif result.ok:
        click.echo("ok")
    else:
        click.echo(f"validation failed\tissues={len(result.issues)}")
    if not result.ok:
        raise SystemExit(1)


@atlas_group.command("status")
@click.option("--path", "repo_path", default=".", show_default=True)
@click.option("--json", "as_json", is_flag=True)
def atlas_status(repo_path: str, as_json: bool) -> None:
    """Show Atlas initialization, generation, and freshness status."""
    result = raise_if_error(_service(repo_path).status())
    assert isinstance(result, AtlasStatusResult)
    if as_json:
        emit_json(result)
        return
    _echo_status(result)


@atlas_group.command("refresh")
@click.argument("paths", nargs=-1)
@click.option("--path", "repo_path", default=".", show_default=True)
@click.option("--json", "as_json", is_flag=True)
def atlas_refresh(paths: tuple[str, ...], repo_path: str, as_json: bool) -> None:
    """Refresh Atlas evidence after source changes."""
    result = raise_if_error(
        _service(repo_path).refresh(list(paths) if paths else None),
    )
    assert isinstance(result, AtlasStatusResult)
    if as_json:
        emit_json(result)
        return
    _echo_status(result)


@atlas_group.command("query")
@click.argument("expression")
@click.option("--path", "repo_path", default=".", show_default=True)
@click.option("--json", "as_json", is_flag=True)
def atlas_query(expression: str, repo_path: str, as_json: bool) -> None:
    """Query local Atlas entities with a minimal DSL expression."""
    result = raise_if_error(_query(repo_path).query(expression))
    assert isinstance(result, AtlasQueryResult)
    if as_json:
        emit_json(result)
        return
    if result.entity is not None:
        metadata = result.entity.get("metadata") if isinstance(result.entity, dict) else None
        entity_id = metadata.get("id") if isinstance(metadata, dict) else result.entity.get("id")
        click.echo(f"ok\t{entity_id or '-'}")
        return
    if result.entities:
        click.echo(f"ok\tentities={len(result.entities)}")
        return
    if result.nodes:
        click.echo(f"ok\tnodes={len(result.nodes)}")
        return
    click.echo("ok" if result.ok else "not found")


__all__ = ["atlas_group"]

#!/usr/bin/env python
"""CLI for Semantic Repository Knowledge Graph commands (RFC-0010)."""

from __future__ import annotations

from typing import Optional

import click

from metagit.cli.commands.acl_common import emit_json, raise_if_error, resolve_acl_roots
from metagit.core.semantic import (
    ConceptConflictsResult,
    ConceptDeclareResult,
    ConceptOwnersResult,
    ConceptQueryResult,
    SemanticGraphService,
)


@click.group(name="semantic")
@click.pass_context
def semantic_group(ctx: click.Context) -> None:
    """Manage semantic concept ownership."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@semantic_group.command("declare")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--concept", required=True)
@click.option("--repository", required=True)
@click.option("--pattern", "patterns", multiple=True, required=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def semantic_declare(
    ctx: click.Context,
    definition_path: str,
    concept: str,
    repository: str,
    patterns: tuple[str, ...],
    as_json: bool,
) -> None:
    """Declare semantic ownership for repository path patterns."""
    service = _service(ctx, definition_path)
    result = raise_if_error(
        service.declare(
            concept=concept,
            repository=repository,
            patterns=list(patterns),
        ),
    )
    assert isinstance(result, ConceptDeclareResult)
    if as_json:
        emit_json(result)
        return
    click.echo(
        f"{result.concept.concept_id}\t{result.ownership.repository}\t{','.join(result.ownership.patterns)}",
    )


@semantic_group.command("query")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--concept", required=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def semantic_query(
    ctx: click.Context,
    definition_path: str,
    concept: str,
    as_json: bool,
) -> None:
    """Query a semantic concept and its ownership declarations."""
    service = _service(ctx, definition_path)
    result = raise_if_error(service.query(concept=concept))
    assert isinstance(result, ConceptQueryResult)
    if as_json:
        emit_json(result)
        return
    if result.concept is None:
        click.echo("No concept found.")
        return
    click.echo(f"{result.concept.concept_id}\t{result.concept.name}")
    for ownership in result.ownerships:
        click.echo(f"  {ownership.repository}\t{','.join(ownership.patterns)}")


@semantic_group.command("owners")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--path", "owned_path", required=True)
@click.option("--repository", required=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def semantic_owners(
    ctx: click.Context,
    definition_path: str,
    owned_path: str,
    repository: str,
    as_json: bool,
) -> None:
    """Resolve semantic concepts that own a repository path."""
    service = _service(ctx, definition_path)
    result = raise_if_error(service.owners(path=owned_path, repository=repository))
    assert isinstance(result, ConceptOwnersResult)
    if as_json:
        emit_json(result)
        return
    if not result.concepts:
        click.echo("No concept owners.")
        return
    for concept in result.concepts:
        click.echo(f"{concept.concept_id}\t{concept.name}")


@semantic_group.command("conflicts")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--repository", required=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def semantic_conflicts(
    ctx: click.Context,
    definition_path: str,
    repository: str,
    as_json: bool,
) -> None:
    """Show advisory concept conflict hints for active ACL claims."""
    service = _service(ctx, definition_path)
    result = raise_if_error(service.conflicts(repository=repository))
    assert isinstance(result, ConceptConflictsResult)
    if as_json:
        emit_json(result)
        return
    if not result.hints:
        click.echo("No semantic conflict hints.")
        return
    for hint in result.hints:
        click.echo(f"{hint.concept_id}\t{','.join(hint.agent_ids)}")


@semantic_group.command("ingest")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--project", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def semantic_ingest(
    ctx: click.Context,
    definition_path: str,
    project: Optional[str],
    as_json: bool,
) -> None:
    """Stub semantic ingest until RFC-0010 Task 8."""
    _ = resolve_acl_roots(ctx, definition_path)
    payload = {
        "ok": True,
        "added": 0,
        "updated": 0,
        "project": project,
        "message": "semantic ingest is deferred until RFC-0010 Task 8",
    }
    if as_json:
        emit_json(payload)
        return
    click.echo(payload["message"])


@semantic_group.command("seed")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def semantic_seed(
    ctx: click.Context,
    definition_path: str,
    as_json: bool,
) -> None:
    """Stub semantic seed until RFC-0010 Task 8."""
    _ = resolve_acl_roots(ctx, definition_path)
    payload = {
        "ok": True,
        "added": 0,
        "updated": 0,
        "message": "semantic seed is deferred until RFC-0010 Task 8",
    }
    if as_json:
        emit_json(payload)
        return
    click.echo(payload["message"])


def _service(ctx: click.Context, definition_path: str) -> SemanticGraphService:
    roots = resolve_acl_roots(ctx, definition_path)
    return SemanticGraphService(roots.session_root)


__all__ = ["semantic_group"]

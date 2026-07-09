#!/usr/bin/env python
"""CLI for merge orchestrator commands (RFC-0011)."""

from __future__ import annotations

import json

import click

from metagit.cli.commands.acl_common import emit_json, raise_if_error, resolve_acl_roots
from metagit.core.merge import MergeOrchestrator, MergeRequest, merge_validators_from_config


@click.group(name="merge")
@click.pass_context
def merge_group(ctx: click.Context) -> None:
  """Manage local merge orchestration records."""
  if ctx.invoked_subcommand is None:
    click.echo(ctx.get_help())


@merge_group.command("enqueue")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--repository", required=True)
@click.option("--branch", "source_branch", required=True)
@click.option("--into", "target_branch", required=True)
@click.option("--node-id", default=None)
@click.option("--agent-id", default=None)
@click.option("--repo-path", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def merge_enqueue(
  ctx: click.Context,
  definition_path: str,
  repository: str,
  source_branch: str,
  target_branch: str,
  node_id: str | None,
  agent_id: str | None,
  repo_path: str | None,
  as_json: bool,
) -> None:
  """Enqueue an agent branch merge into an integration branch."""
  service = _service(ctx, definition_path)
  result = raise_if_error(
    service.enqueue(
      repository,
      source_branch,
      target_branch,
      node_id=node_id,
      agent_id=agent_id,
      repo_path=repo_path,
    )
  )
  assert isinstance(result, MergeRequest)
  if as_json:
    emit_json(result)
    return
  click.echo(f"{result.merge_id}\t{result.repository}\t{result.status}")


@merge_group.command("status")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--repository", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def merge_status(
  ctx: click.Context,
  definition_path: str,
  repository: str | None,
  as_json: bool,
) -> None:
  """List merge requests."""
  service = _service(ctx, definition_path)
  result = raise_if_error(service.status(repository=repository))
  rows = [row.model_dump(mode="json") for row in result]
  if as_json:
    click.echo(json.dumps(rows, indent=2))
    return
  if not rows:
    click.echo("No merge requests.")
    return
  for row in rows:
    click.echo(f"{row['merge_id']}\t{row['repository']}\t{row['status']}")


@merge_group.command("integrate")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--merge-id", required=True)
@click.option("--repo-path", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def merge_integrate(
  ctx: click.Context,
  definition_path: str,
  merge_id: str,
  repo_path: str | None,
  as_json: bool,
) -> None:
  """Attempt the queued merge."""
  service = _service(ctx, definition_path)
  _apply_repo_path(service, merge_id, repo_path)
  result = raise_if_error(service.integrate(merge_id))
  assert isinstance(result, MergeRequest)
  _emit_request(result, as_json)


@merge_group.command("retry")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--merge-id", required=True)
@click.option("--repo-path", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def merge_retry(
  ctx: click.Context,
  definition_path: str,
  merge_id: str,
  repo_path: str | None,
  as_json: bool,
) -> None:
  """Retry a failed, conflicting, or validation-failed merge."""
  service = _service(ctx, definition_path)
  _apply_repo_path(service, merge_id, repo_path)
  result = raise_if_error(service.retry(merge_id))
  assert isinstance(result, MergeRequest)
  _emit_request(result, as_json)


@merge_group.command("promote")
@click.option("--definition", "definition_path", default=".metagit.yml", show_default=True)
@click.option("--merge-id", required=True)
@click.option("--into", "into_branch", required=True)
@click.option("--repo-path", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_context
def merge_promote(
  ctx: click.Context,
  definition_path: str,
  merge_id: str,
  into_branch: str,
  repo_path: str | None,
  as_json: bool,
) -> None:
  """Promote a validated integration branch into another branch."""
  service = _service(ctx, definition_path)
  _apply_repo_path(service, merge_id, repo_path)
  result = raise_if_error(service.promote(merge_id, into_branch))
  assert isinstance(result, MergeRequest)
  _emit_request(result, as_json)


def _service(ctx: click.Context, definition_path: str) -> MergeOrchestrator:
  roots = resolve_acl_roots(ctx, definition_path)
  config = ctx.obj.get("config") if ctx.obj else None
  return MergeOrchestrator(
    roots.session_root,
    validators=merge_validators_from_config(config),
  )


def _apply_repo_path(service: MergeOrchestrator, merge_id: str, repo_path: str | None) -> None:
  if repo_path is None:
    return
  request = raise_if_error(service.store.load(merge_id))
  assert isinstance(request, MergeRequest)
  request.repo_path = repo_path
  saved = service.store.save(request)
  if isinstance(saved, Exception):
    raise click.ClickException(str(saved))


def _emit_request(request: MergeRequest, as_json: bool) -> None:
  if as_json:
    emit_json(request)
    return
  click.echo(f"{request.merge_id}\t{request.repository}\t{request.status}")


__all__ = ["merge_group"]

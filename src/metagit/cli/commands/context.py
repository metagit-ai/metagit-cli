#!/usr/bin/env python
"""
Context pack CLI: workspace map (tier 0), repo cards (tier 1), session digest (tier 2).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click

from metagit.core.appconfig import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.context.approval_service import ApprovalService
from metagit.core.context.context_pack_service import ContextPackService
from metagit.core.context.models import (
    ContextPackResult,
    RepoCardResult,
    SessionDigestResult,
)
from metagit.core.context.objective_service import ObjectiveService
from metagit.core.context.repo_card_service import RepoCardService
from metagit.core.context.repomix_profile_service import RepomixProfileService
from metagit.core.workspace.root_resolver import (
    resolve_definition_root,
    resolve_session_root,
    resolve_sync_root,
)
from metagit.cli.shell_completion import (
    complete_projects,
    complete_repos,
    complete_repomix_profiles,
)


def _load_manifest(definition_path: str) -> MetagitConfig:
    manager = MetagitConfigManager(definition_path)
    loaded = manager.load_config()
    if isinstance(loaded, Exception):
        raise click.ClickException(str(loaded))
    return loaded


def _context_paths(
    ctx: click.Context,
    definition_path: str,
) -> tuple[MetagitConfig, str, str, str, AppConfig]:
    """Return manifest, config path, sync root, session root, and app config."""
    app_config: AppConfig = ctx.obj["config"]
    config = _load_manifest(definition_path)
    config_path = str(Path(definition_path).expanduser().resolve())
    definition_root = resolve_definition_root(definition_path)
    sync_root = resolve_sync_root(definition_root, app_config.workspace.path)
    session_root = resolve_session_root(definition_root)
    return config, config_path, sync_root, session_root, app_config


def _summarize_digest_line(digest: SessionDigestResult) -> None:
    click.echo(
        f"digest: tier=2 since={digest.since!r} first_session={digest.first_session}"
    )
    if digest.manifest_changed:
        click.echo("  manifest changed vs session boundary")
    if digest.active_objective_id:
        click.echo(f"  active objective: {digest.active_objective_id}")
    if digest.repo_changes:
        click.echo(f"  repo activity rows: {len(digest.repo_changes)}")
        for row in digest.repo_changes[:8]:
            err = f" err={row.error}" if row.error else ""
            click.echo(
                f"    {row.project_name}/{row.repo_name}: {row.commit_count} commits{err}",
            )


def _summarize_pack(pack: ContextPackResult) -> None:
    click.echo(f"workspace: {pack.workspace_name}")
    click.echo(f"tier: {pack.tier}")
    if pack.map:
        mp = pack.map
        click.echo(
            "map: "
            f"{mp.project_count} project(s), {mp.repo_count} repo(s); "
            f"root={mp.workspace_root}"
        )
        if mp.projects:
            names = ", ".join(p.name for p in mp.projects[:8])
            suffix = "" if len(mp.projects) <= 8 else ", …"
            click.echo(f"  projects: {names}{suffix}")
    if pack.tier in (1, 2) and pack.cards is not None:
        click.echo(f"cards: {len(pack.cards)} repo card(s)")
        for card in pack.cards[:10]:
            _summarize_card_line(card)
        if len(pack.cards) > 10:
            click.echo("  …")
        if pack.tier == 2 and pack.digest is not None:
            _summarize_digest_line(pack.digest)


def _summarize_card_line(card: RepoCardResult) -> None:
    flags = f" [{' '.join(card.health_flags)}]" if card.health_flags else ""
    git_bits = ""
    if card.exists and card.is_git_repo:
        git_bits = f" branch={card.branch}"
        if card.dirty:
            git_bits += " dirty"
    click.echo(
        f"  {card.project_name}/{card.repo_name}: {card.status}{git_bits}{flags}",
    )


def _summarize_card(card: RepoCardResult) -> None:
    click.echo(f"{card.project_name}/{card.repo_name}")
    click.echo(f"  path: {card.repo_path}")
    click.echo(f"  status: {card.status} exists={card.exists} git={card.is_git_repo}")
    if card.exists and card.is_git_repo:
        click.echo(
            "  git: "
            f"branch={card.branch} ahead={card.ahead} behind={card.behind} "
            f"dirty={card.dirty}",
        )
    if card.health_flags:
        click.echo(f"  health: {' '.join(card.health_flags)}")
    if card.stack_hints:
        click.echo(f"  stack: {', '.join(card.stack_hints[:6])}")


@click.group(name="context", invoke_without_command=True)
@click.pass_context
def context(ctx: click.Context) -> None:
    """Workspace context packs (tiered map and repo cards)."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@context.command("pack")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
    help="Path to the workspace .metagit.yml definition file",
)
@click.option(
    "--tier",
    type=click.IntRange(0, 2),
    required=True,
    help=(
        "0 = workspace map only; 1 = map + repo cards; "
        "2 = tier 1 + session digest then touch session boundary"
    ),
)
@click.option(
    "--project",
    "project_name",
    default=None,
    help="Limit cards (tier 1+)",
    shell_complete=complete_projects,
)
@click.option(
    "--repo",
    "repo_name",
    default=None,
    help="Limit cards (tier 1+)",
    shell_complete=complete_repos,
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print ContextPackResult as JSON",
)
@click.pass_context
def pack_cmd(
    ctx: click.Context,
    definition_path: str,
    tier: int,
    project_name: str | None,
    repo_name: str | None,
    as_json: bool,
) -> None:
    """Emit a tiered context pack (workspace map ± repo cards ± digest)."""
    config, config_path, sync_root, session_root, _ = _context_paths(
        ctx,
        definition_path,
    )
    definition_root = resolve_definition_root(definition_path)
    svc = ContextPackService()
    result = svc.pack(
        config=config,
        config_path=config_path,
        workspace_root=sync_root,
        session_root=session_root,
        definition_root=definition_root,
        tier=tier,
        project_name=project_name,
        repo_name=repo_name,
    )
    if as_json:
        click.echo(result.model_dump_json(indent=2))
        return
    _summarize_pack(result)


@context.command("repo-card")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
    help="Path to the workspace .metagit.yml definition file",
)
@click.option(
    "--project", "project_name", required=True, shell_complete=complete_projects
)
@click.option("--repo", "repo_name", required=True, shell_complete=complete_repos)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Print RepoCardResult as JSON",
)
@click.pass_context
def repo_card_cmd(
    ctx: click.Context,
    definition_path: str,
    project_name: str,
    repo_name: str,
    as_json: bool,
) -> None:
    """Emit a single tier-1 repo card."""
    config, _, sync_root, _, _ = _context_paths(ctx, definition_path)
    definition_root = resolve_definition_root(definition_path)
    try:
        card = RepoCardService().build_one(
            config,
            sync_root,
            project_name,
            repo_name,
            definition_root=definition_root,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        click.echo(card.model_dump_json(indent=2))
        return
    _summarize_card(card)


@context.command("repomix")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
    help="Path to the workspace .metagit.yml definition file",
)
@click.option(
    "--profile", "profile_name", required=True, shell_complete=complete_repomix_profiles
)
@click.option(
    "--project", "project_name", required=True, shell_complete=complete_projects
)
@click.option("--repo", "repo_name", required=True, shell_complete=complete_repos)
@click.option(
    "--output",
    "output_path",
    default=None,
    help="Write repomix output to this path instead of stdout",
)
@click.pass_context
def repomix_cmd(
    ctx: click.Context,
    definition_path: str,
    profile_name: str,
    project_name: str,
    repo_name: str,
    output_path: str | None,
) -> None:
    """Run repomix with a bundled context profile for one managed repo."""
    config, _, sync_root, _, _ = _context_paths(ctx, definition_path)
    definition_root = resolve_definition_root(definition_path)
    try:
        card = RepoCardService().build_one(
            config,
            sync_root,
            project_name,
            repo_name,
            definition_root=definition_root,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    svc = RepomixProfileService()
    try:
        if output_path:
            resolved = svc.run_repomix(
                card.repo_path,
                profile_name,
                output_path=output_path,
                stdout=False,
            )
            click.echo(str(resolved))
        else:
            text = svc.run_repomix(
                card.repo_path,
                profile_name,
                output_path=None,
                stdout=True,
            )
            click.echo(text)
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


@context.group("objective")
def objective_group() -> None:
    """List, read, and update workspace objectives."""


@objective_group.command("list")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
)
@click.pass_context
def objective_list_cmd(
    ctx: click.Context,
    definition_path: str,
    as_json: bool,
) -> None:
    """List objectives persisted under `.metagit/sessions/objectives.json`."""
    _, _, _, session_root, _ = _context_paths(ctx, definition_path)
    result = ObjectiveService(workspace_root=session_root).list()
    if as_json:
        click.echo(result.model_dump_json(indent=2))
        return
    if not result.objectives:
        click.echo("No objectives.")
        return
    for obj in result.objectives:
        click.echo(
            f"{obj.id} [{obj.status}] {obj.title} "
            f"repos={','.join(obj.repos) if obj.repos else '—'}",
        )


def _resolve_objective_dict_from_cli(
    stdin_obj: dict[str, Any],
    *,
    objective_id: str | None,
    title: str | None,
    status: str | None,
    repos_tuple: tuple[str, ...],
) -> dict[str, Any]:
    merged = dict(stdin_obj)
    if objective_id:
        merged["id"] = objective_id
    if title is not None:
        merged["title"] = title
    if status is not None:
        merged["status"] = status
    if repos_tuple:
        merged["repos"] = list(repos_tuple)
    return merged


@objective_group.command("set")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--id", "objective_id")
@click.option("--title")
@click.option(
    "--status",
    type=click.Choice(["pending", "in_progress", "done", "cancelled"]),
)
@click.option("--repo", "repos_sel", multiple=True)
@click.pass_context
def objective_set_cmd(
    ctx: click.Context,
    definition_path: str,
    objective_id: str | None,
    title: str | None,
    status: str | None,
    repos_sel: tuple[str, ...],
) -> None:
    """Upsert an objective from JSON on stdin or from flags (--id and --title)."""
    base: dict[str, Any]
    if not sys.stdin.isatty():
        raw_stdin = sys.stdin.read().strip()
        if raw_stdin:
            try:
                parsed = json.loads(raw_stdin)
            except json.JSONDecodeError as exc:
                raise click.ClickException(f"stdin JSON invalid: {exc}") from exc
            if not isinstance(parsed, dict):
                raise click.ClickException("stdin JSON must be an object")
            base = parsed
        else:
            base = {}
    else:
        base = {}
    merged = _resolve_objective_dict_from_cli(
        base,
        objective_id=objective_id,
        title=title,
        status=status,
        repos_tuple=repos_sel,
    )
    if "id" not in merged or not str(merged.get("id", "")).strip():
        raise click.ClickException("objective id is required (stdin or --id)")
    _, _, _, session_root, _ = _context_paths(ctx, definition_path)
    svc = ObjectiveService(workspace_root=session_root)
    try:
        saved = svc.upsert_partial(merged)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(saved.model_dump_json(indent=2))


@objective_group.command("get")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--id", "objective_id", required=True)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
)
@click.pass_context
def objective_get_cmd(
    ctx: click.Context,
    definition_path: str,
    objective_id: str,
    as_json: bool,
) -> None:
    """Print one objective by id."""
    _, _, _, session_root, _ = _context_paths(ctx, definition_path)
    obj = ObjectiveService(workspace_root=session_root).get(objective_id=objective_id)
    if obj is None:
        raise click.ClickException(f"objective not found: {objective_id}")
    if as_json:
        click.echo(obj.model_dump_json(indent=2))
        return
    click.echo(
        f"{obj.id} [{obj.status}] {obj.title}\nrepos: {', '.join(obj.repos) or '—'}",
    )


@objective_group.command("complete")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--id", "objective_id", required=True)
@click.pass_context
def objective_complete_cmd(
    ctx: click.Context,
    definition_path: str,
    objective_id: str,
) -> None:
    """Mark an objective done."""
    _, _, _, session_root, _ = _context_paths(ctx, definition_path)
    try:
        saved = ObjectiveService(workspace_root=session_root).complete(
            objective_id=objective_id,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(saved.model_dump_json(indent=2))


@objective_group.command("cancel")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--id", "objective_id", required=True)
@click.pass_context
def objective_cancel_cmd(
    ctx: click.Context,
    definition_path: str,
    objective_id: str,
) -> None:
    """Mark an objective cancelled."""
    _, _, _, session_root, _ = _context_paths(ctx, definition_path)
    try:
        saved = ObjectiveService(workspace_root=session_root).cancel(
            objective_id=objective_id,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(saved.model_dump_json(indent=2))


@context.group("approval")
def approval_group() -> None:
    """Human-in-the-loop approval queue."""


@approval_group.command("list")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option(
    "--status",
    "status_filter",
    type=click.Choice(["pending", "approved", "denied", "all"]),
    default="pending",
    show_default=True,
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
)
@click.pass_context
def approval_list_cmd(
    ctx: click.Context,
    definition_path: str,
    status_filter: str,
    as_json: bool,
) -> None:
    """List approval requests (pending by default)."""
    _, _, _, session_root, _ = _context_paths(ctx, definition_path)
    svc = ApprovalService(workspace_root=session_root)
    result = (
        svc.list(status=None)
        if status_filter == "all"
        else svc.list(status=status_filter)
    )
    if as_json:
        click.echo(result.model_dump_json(indent=2))
        return
    if not result.requests:
        click.echo("No approval requests.")
        return
    for req in result.requests:
        note = req.resolver_note or "—"
        click.echo(
            f"{req.id} [{req.status}] {req.action} by={req.requested_by} note={note}"
        )


@approval_group.command("approve")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--id", "approval_id", required=True)
@click.option("--note", "resolver_note", default=None)
@click.pass_context
def approval_approve_cmd(
    ctx: click.Context,
    definition_path: str,
    approval_id: str,
    resolver_note: str | None,
) -> None:
    """Approve a pending request."""
    _, _, _, session_root, _ = _context_paths(ctx, definition_path)
    try:
        row = ApprovalService(workspace_root=session_root).resolve(
            request_id=approval_id,
            decision="approved",
            note=resolver_note,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(row.model_dump_json(indent=2))


def _resolve_approval_dict_from_cli(
    stdin_obj: dict[str, Any],
    *,
    action: str | None,
    requested_by: str | None,
    payload_json: str | None,
) -> dict[str, Any]:
    merged = dict(stdin_obj)
    if action is not None:
        merged["action"] = action
    if requested_by is not None:
        merged["requested_by"] = requested_by
    if payload_json is not None:
        try:
            parsed_payload = json.loads(payload_json)
        except json.JSONDecodeError as exc:
            raise click.ClickException(f"--payload JSON invalid: {exc}") from exc
        if not isinstance(parsed_payload, dict):
            raise click.ClickException("--payload JSON must be an object")
        merged["payload"] = parsed_payload
    return merged


@approval_group.command("request")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--action")
@click.option("--requested-by", "requested_by")
@click.option("--payload", "payload_json", default=None, help="JSON object string")
@click.pass_context
def approval_request_cmd(
    ctx: click.Context,
    definition_path: str,
    action: str | None,
    requested_by: str | None,
    payload_json: str | None,
) -> None:
    """Create an approval request from JSON on stdin or flags."""
    base: dict[str, Any]
    if not sys.stdin.isatty():
        raw_stdin = sys.stdin.read().strip()
        if raw_stdin:
            try:
                parsed = json.loads(raw_stdin)
            except json.JSONDecodeError as exc:
                raise click.ClickException(f"stdin JSON invalid: {exc}") from exc
            if not isinstance(parsed, dict):
                raise click.ClickException("stdin JSON must be an object")
            base = parsed
        else:
            base = {}
    else:
        base = {}
    merged = _resolve_approval_dict_from_cli(
        base,
        action=action,
        requested_by=requested_by,
        payload_json=payload_json,
    )
    action_val = str(merged.get("action") or "").strip()
    if not action_val:
        raise click.ClickException("action is required (stdin or --action)")
    requester = str(merged.get("requested_by") or "agent").strip() or "agent"
    payload_raw = merged.get("payload")
    payload = dict(payload_raw) if isinstance(payload_raw, dict) else {}
    _, _, _, session_root, _ = _context_paths(ctx, definition_path)
    row = ApprovalService(workspace_root=session_root).request(
        action=action_val,
        payload=payload,
        requested_by=requester,
    )
    click.echo(row.model_dump_json(indent=2))


@approval_group.command("deny")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option("--id", "approval_id", required=True)
@click.option("--note", "resolver_note", required=True)
@click.pass_context
def approval_deny_cmd(
    ctx: click.Context,
    definition_path: str,
    approval_id: str,
    resolver_note: str,
) -> None:
    """Deny a pending request (note required)."""
    _, _, _, session_root, _ = _context_paths(ctx, definition_path)
    try:
        row = ApprovalService(workspace_root=session_root).resolve(
            request_id=approval_id,
            decision="denied",
            note=resolver_note,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(row.model_dump_json(indent=2))

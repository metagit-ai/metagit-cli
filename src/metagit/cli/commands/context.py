#!/usr/bin/env python
"""
Context pack CLI: workspace map (tier 0) and repo cards (tier 1).
"""

from __future__ import annotations

from pathlib import Path

import click

from metagit.core.appconfig import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.context.context_pack_service import ContextPackService
from metagit.core.context.models import ContextPackResult, RepoCardResult
from metagit.core.context.repo_card_service import RepoCardService


def _load_manifest(definition_path: str) -> MetagitConfig:
    manager = MetagitConfigManager(definition_path)
    loaded = manager.load_config()
    if isinstance(loaded, Exception):
        raise click.ClickException(str(loaded))
    return loaded


def _context_paths(
    ctx: click.Context,
    definition_path: str,
) -> tuple[MetagitConfig, str, str, AppConfig]:
    """Return manifest config, resolved definition path, workspace root, app config."""
    app_config: AppConfig = ctx.obj["config"]
    config = _load_manifest(definition_path)
    workspace_root = str(Path(app_config.workspace.path).expanduser().resolve())
    config_path = str(Path(definition_path).expanduser().resolve())
    return config, config_path, workspace_root, app_config


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
    if pack.tier == 1 and pack.cards is not None:
        click.echo(f"cards: {len(pack.cards)} repo card(s)")
        for card in pack.cards[:10]:
            _summarize_card_line(card)
        if len(pack.cards) > 10:
            click.echo("  …")


def _summarize_card_line(card: RepoCardResult) -> None:
    flags = f" [{' '.join(card.health_flags)}]" if card.health_flags else ""
    git_bits = ""
    if card.exists and card.is_git_repo:
        git_bits = f" branch={card.branch}"
        if card.dirty:
            git_bits += " dirty"
    click.echo(
        f"  {card.project_name}/{card.repo_name}: {card.status}{git_bits}{flags}"
    )


def _summarize_card(card: RepoCardResult) -> None:
    click.echo(f"{card.project_name}/{card.repo_name}")
    click.echo(f"  path: {card.repo_path}")
    click.echo(f"  status: {card.status} exists={card.exists} git={card.is_git_repo}")
    if card.exists and card.is_git_repo:
        click.echo(
            "  git: "
            f"branch={card.branch} ahead={card.ahead} behind={card.behind} "
            f"dirty={card.dirty}"
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
    type=click.IntRange(0, 1),
    required=True,
    help="0 = workspace map only; 1 = map + repo cards",
)
@click.option("--project", "project_name", default=None, help="Limit cards (tier 1)")
@click.option("--repo", "repo_name", default=None, help="Limit cards (tier 1)")
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
    """Emit a tiered context pack (workspace map ± repo cards)."""
    config, config_path, workspace_root, _ = _context_paths(ctx, definition_path)
    svc = ContextPackService()
    result = svc.pack(
        config=config,
        config_path=config_path,
        workspace_root=workspace_root,
        tier=tier,  # type: ignore[arg-type]
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
@click.option("--project", "project_name", required=True)
@click.option("--repo", "repo_name", required=True)
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
    config, _, workspace_root, _ = _context_paths(ctx, definition_path)
    try:
        card = RepoCardService().build_one(
            config,
            workspace_root,
            project_name,
            repo_name,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if as_json:
        click.echo(card.model_dump_json(indent=2))
        return
    _summarize_card(card)

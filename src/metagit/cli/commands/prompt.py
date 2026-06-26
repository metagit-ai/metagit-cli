#!/usr/bin/env python
"""
Emit metagit prompts for workspace, project, and repo scopes.
"""

from __future__ import annotations

from pathlib import Path

import click

from metagit.cli.json_output import emit_json
from metagit.core.appconfig import AppConfig
from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.prompt.catalog import kinds_for_scope
from metagit.core.prompt.service import PromptService, PromptServiceError


def _load_manifest(definition_path: str) -> MetagitConfig:
    manager = MetagitConfigManager(definition_path)
    loaded = manager.load_config()
    if isinstance(loaded, Exception):
        raise click.ClickException(str(loaded))
    return loaded


def _prompt_ctx(
    ctx: click.Context,
    definition_path: str,
) -> tuple[MetagitConfig, str, str, AppConfig]:
    app_config: AppConfig = ctx.obj["config"]
    config = _load_manifest(definition_path)
    workspace_root = str(Path(app_config.workspace.path).expanduser().resolve())
    return config, definition_path, workspace_root, app_config


def _kind_choice(scope: str) -> click.Choice:
    return click.Choice(
        [str(item) for item in kinds_for_scope(scope)],  # type: ignore[arg-type]
        case_sensitive=False,
    )


def _run_emit(
    ctx: click.Context,
    *,
    scope: str,
    definition_path: str,
    kind: str,
    project_name: str | None,
    repo_name: str | None,
    no_instructions: bool,
    as_json: bool,
    text_only: bool,
) -> None:
    config, def_path, workspace_root, app_config = _prompt_ctx(ctx, definition_path)
    try:
        result = PromptService().emit(
            config,
            kind=kind,  # type: ignore[arg-type]
            scope=scope,  # type: ignore[arg-type]
            definition_path=def_path,
            workspace_root=workspace_root,
            project_name=project_name,
            repo_name=repo_name,
            include_instructions=not no_instructions,
            workspace_dedupe=app_config.workspace.dedupe,
        )
    except PromptServiceError as exc:
        raise click.ClickException(str(exc)) from exc

    if text_only:
        click.echo(result.text, nl=result.text.endswith("\n"))
        return
    if as_json:
        emit_json(result)
        return
    click.echo(result.text)
    if result.instruction_layers and kind != "instructions":
        click.echo("\n---\n")
        click.echo(f"({len(result.instruction_layers)} instruction layer(s) included)")


@click.group(name="prompt", invoke_without_command=True)
@click.pass_context
def prompt(ctx: click.Context) -> None:
    """Emit metagit prompts for workspace, project, and repo scopes."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@prompt.command("list")
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.pass_context
def prompt_list(ctx: click.Context, as_json: bool) -> None:
    """List available prompt kinds and valid scopes."""
    _ = ctx
    entries = PromptService().list_entries()
    if as_json:
        emit_json({"prompts": [item.model_dump(mode="json") for item in entries]})
        return
    for entry in entries:
        scopes = ", ".join(entry.scopes)
        click.echo(f"{entry.kind}\t{entry.title}\t(scopes: {scopes})")
        click.echo(f"  {entry.description}")


@prompt.command("workspace")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
    help="Path to the workspace .metagit.yml definition file",
)
@click.option(
    "--kind",
    "-k",
    "kind",
    type=_kind_choice("workspace"),
    default="instructions",
    show_default=True,
    help="Prompt kind to emit",
)
@click.option(
    "--no-instructions",
    is_flag=True,
    default=False,
    help="Omit composed manifest instructions from operational prompts",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Print JSON for agents")
@click.option(
    "--text-only",
    is_flag=True,
    default=False,
    help="Print prompt text only (no JSON wrapper)",
)
@click.pass_context
def prompt_workspace(
    ctx: click.Context,
    definition_path: str,
    kind: str,
    no_instructions: bool,
    as_json: bool,
    text_only: bool,
) -> None:
    """Emit a prompt for the whole workspace manifest."""
    _run_emit(
        ctx,
        scope="workspace",
        definition_path=definition_path,
        kind=kind,
        project_name=None,
        repo_name=None,
        no_instructions=no_instructions,
        as_json=as_json,
        text_only=text_only,
    )


@prompt.command("project")
@click.option("--project", "-p", "project_name", required=True, help="Workspace project name")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option(
    "--kind",
    "-k",
    "kind",
    type=_kind_choice("project"),
    default="instructions",
    show_default=True,
)
@click.option("--no-instructions", is_flag=True, default=False)
@click.option("--json", "as_json", is_flag=True, default=False)
@click.option("--text-only", is_flag=True, default=False)
@click.pass_context
def prompt_project(
    ctx: click.Context,
    project_name: str,
    definition_path: str,
    kind: str,
    no_instructions: bool,
    as_json: bool,
    text_only: bool,
) -> None:
    """Emit a prompt scoped to one workspace project."""
    _run_emit(
        ctx,
        scope="project",
        definition_path=definition_path,
        kind=kind,
        project_name=project_name,
        repo_name=None,
        no_instructions=no_instructions,
        as_json=as_json,
        text_only=text_only,
    )


@prompt.command("repo")
@click.option("--project", "-p", "project_name", required=True, help="Workspace project name")
@click.option("--repo", "-n", "repo_name", required=True, help="Repository name")
@click.option(
    "--definition",
    "-c",
    "definition_path",
    default=".metagit.yml",
    show_default=True,
)
@click.option(
    "--kind",
    "-k",
    "kind",
    type=_kind_choice("repo"),
    default="instructions",
    show_default=True,
)
@click.option("--no-instructions", is_flag=True, default=False)
@click.option("--json", "as_json", is_flag=True, default=False)
@click.option("--text-only", is_flag=True, default=False)
@click.pass_context
def prompt_repo(
    ctx: click.Context,
    project_name: str,
    repo_name: str,
    definition_path: str,
    kind: str,
    no_instructions: bool,
    as_json: bool,
    text_only: bool,
) -> None:
    """Emit a prompt scoped to one repository entry."""
    _run_emit(
        ctx,
        scope="repo",
        definition_path=definition_path,
        kind=kind,
        project_name=project_name,
        repo_name=repo_name,
        no_instructions=no_instructions,
        as_json=as_json,
        text_only=text_only,
    )

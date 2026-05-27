#!/usr/bin/env python
"""
Init subcommand

Creates a validated `.metagit.yml` from bundled templates (copier-style prompts or
answers files) or from a minimal kind profile aligned with the current schema.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

import click
from git import Repo

from metagit.core.appconfig import AppConfig
from metagit.core.init.service import InitService
from metagit.core.project.models import ProjectKind
from metagit.core.utils.logging import UnifiedLogger


def _resolve_project_metadata(directory: Path) -> Tuple[str, Optional[str]]:
    """
    Resolve project name and optional remote URL from a directory.

    Works inside a Git repository or any ordinary folder.
    """
    name = directory.name
    url: Optional[str] = None
    try:
        git_repo = Repo(directory)
        name = Path(git_repo.working_dir).name
        if git_repo.remotes:
            remote_url = git_repo.remotes[0].url
            url = remote_url if remote_url else None
    except Exception:
        pass
    return name, url


def _kind_choice() -> list[str]:
    return [item.value for item in ProjectKind]


def resolve_target_dir(
    target: str,
    *,
    create: bool = False,
) -> Path:
    """
    Resolve and validate the directory to initialize.

    Args:
        target: Path string (relative, absolute, or ~).
        create: When true, create the directory tree if missing.

    Returns:
        Absolute resolved target path.
    """
    path = Path(target).expanduser().resolve()
    if path.is_dir():
        return path
    if path.exists():
        raise click.ClickException(f"Target path exists but is not a directory: {path}")
    if create:
        path.mkdir(parents=True, exist_ok=False)
        return path
    raise click.ClickException(
        f"Target directory does not exist: {path} (use --create to create it)"
    )


@click.command("init")
@click.argument(
    "target",
    required=False,
    default=".",
    type=click.Path(file_okay=False, dir_okay=True),
)
@click.option(
    "--target",
    "target_option",
    default=None,
    type=click.Path(file_okay=False, dir_okay=True),
    help="Target folder to initialize (overrides positional TARGET)",
)
@click.option(
    "--create",
    is_flag=True,
    help="Create the target directory if it does not exist",
)
@click.option(
    "--template",
    "-t",
    "template",
    default=None,
    help="Bundled init template id (see --list-templates)",
)
@click.option(
    "--list-templates",
    is_flag=True,
    help="List bundled init templates and exit",
)
@click.option(
    "--answers-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    default=None,
    help="YAML/JSON file with template answers (copier-style)",
)
@click.option(
    "--no-prompt",
    is_flag=True,
    help="Do not prompt; use defaults and answers file only",
)
@click.option(
    "--kind",
    "-k",
    default="application",
    type=click.Choice(_kind_choice(), case_sensitive=False),
    help="Project kind (used when no bundled template exists for this kind)",
)
@click.option(
    "--name",
    "-n",
    default=None,
    help="Override manifest name",
)
@click.option(
    "--description",
    "-d",
    default=None,
    help="Override manifest description",
)
@click.option(
    "--url",
    "-u",
    default=None,
    help="Override manifest git URL",
)
@click.option(
    "--minimal",
    is_flag=True,
    help="Skip bundled templates; write minimal schema-backed manifest for --kind",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing .metagit.yml",
)
@click.option(
    "--skip-gitignore",
    "-s",
    is_flag=True,
    help="Skip updating .gitignore",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate and render without writing files",
)
@click.pass_context
def init(
    ctx: click.Context,
    target: str,
    target_option: Optional[str],
    create: bool,
    template: Optional[str],
    list_templates: bool,
    answers_file: Optional[Path],
    no_prompt: bool,
    kind: str,
    name: Optional[str],
    description: Optional[str],
    url: Optional[str],
    minimal: bool,
    force: bool,
    skip_gitignore: bool,
    dry_run: bool,
) -> None:
    """
    Initialize metagit with a validated manifest and optional companion files.

    TARGET is the folder to write into (default: current directory). Use --target
    to pass a path when you prefer a flag over the positional argument.
    """
    logger: UnifiedLogger = ctx.obj["logger"]
    app_config: AppConfig = ctx.obj["config"]
    service = InitService()
    target_path = resolve_target_dir(
        target_option if target_option is not None else target,
        create=create,
    )

    if list_templates:
        rows = service.list_templates()
        if not rows:
            click.echo("No bundled init templates found.")
            return
        for row in rows:
            click.echo(f"{row.id}\t{row.label}\t(kind={row.kind})")
            click.echo(f"  {row.description.strip()}")
        return

    directory_name, git_url = _resolve_project_metadata(target_path)
    overrides: dict[str, str] = {}
    if name:
        overrides["name"] = name
    if description:
        overrides["description"] = description
    if url is not None:
        overrides["url"] = url

    template_id = service.resolve_template_id(template, kind if not minimal else None)
    manifest = service.registry.load_manifest(template_id)
    use_bundled = manifest is not None and not minimal

    agent_mode = bool(ctx.obj.get("agent_mode", False))
    if agent_mode:
        no_prompt = True

    if (target_path / ".metagit.yml").exists() and force and not dry_run:
        if agent_mode:
            raise click.UsageError(
                "Overwrite confirmation is disabled in agent mode; remove .metagit.yml first or use a new directory"
            )
        if not click.confirm("Overwrite existing .metagit.yml?"):
            ctx.abort()

    try:
        if use_bundled and manifest is not None:
            result = service.initialize(
                target_path,
                template_id=template_id,
                directory_name=directory_name,
                git_remote_url=git_url,
                answers_file=answers_file,
                overrides=overrides,
                no_prompt=no_prompt,
                force=force,
                dry_run=dry_run,
            )
            effective_kind = manifest.kind
        else:
            desc = description or f"{kind} project managed by metagit."
            result = service.initialize_minimal(
                target_path,
                kind=kind,
                name=name or directory_name,
                description=desc,
                url=url if url is not None else git_url,
                force=force,
                dry_run=dry_run,
            )
            effective_kind = kind
    except click.ClickException as exc:
        logger.error(str(exc))
        ctx.abort()

    if dry_run:
        if result.already_exists:
            logger.success("Dry run: existing .metagit.yml is valid (no changes).")
        else:
            logger.success("Dry run: manifest validated (no files written).")
        return

    if result.already_exists:
        logger.success(f"Already initialized: {result.metagit_yml}")
        logger.info("  metagit config validate")
        return

    if not skip_gitignore:
        _update_gitignore(
            os.path.join(target_path, ".gitignore"),
            app_config.workspace.path,
            logger,
        )
    else:
        logger.info("Skipping .gitignore file update")

    logger.success(f"Created {result.metagit_yml}")
    for extra in result.extra_files:
        logger.info(f"Created {extra}")

    _print_next_steps(
        logger,
        effective_kind=effective_kind,
        template_id=template_id if use_bundled else None,
    )


def _print_next_steps(
    logger: UnifiedLogger,
    *,
    effective_kind: str,
    template_id: Optional[str],
) -> None:
    logger.header("Metagit initialization complete!")
    logger.info("  metagit config validate")
    if template_id == "hermes-orchestrator":
        logger.info("  metagit project repo add --project portfolio --prompt")
        logger.info("  metagit project sync --project portfolio")
        logger.info("  metagit project sync --project local")
        logger.info("  metagit mcp serve --root .")
        return
    if effective_kind == "application":
        logger.info("  metagit detect repo --force   # optional discovery")
        logger.info("  metagit project sync --project local   # when using paths block")
        return
    if effective_kind == "umbrella":
        logger.info("  metagit project repo add --project default --prompt")
        logger.info("  metagit project sync")
        return
    logger.info("  metagit project repo add --prompt")


def _sanitize_workspace_path(workspace_path: str) -> str:
    """Sanitize workspace path for .gitignore."""
    if workspace_path.startswith("./"):
        sanitized = workspace_path[2:]
    else:
        sanitized = workspace_path

    return f"{sanitized}/" if not sanitized.endswith("/") else sanitized


def _update_gitignore(
    gitignore_path: str,
    workspace_path: str,
    logger: UnifiedLogger,
) -> None:
    """Update .gitignore file to include workspace path."""
    target_path = _sanitize_workspace_path(workspace_path)
    try:
        if Path(gitignore_path).exists():
            with open(gitignore_path, "r", encoding="utf-8") as handle:
                lines = handle.readlines()

            for line in lines:
                if line.strip() == target_path.strip():
                    logger.info(
                        f"Workspace path already defined in .gitignore: '{target_path}'"
                    )
                    return

            with open(gitignore_path, "a", encoding="utf-8") as handle:
                handle.write(f"\n# Metagit workspace\n{target_path}\n")
            logger.info(f"Added to existing .gitignore: {target_path}")

        else:
            with open(gitignore_path, "w", encoding="utf-8") as handle:
                handle.write(f"# Metagit workspace\n{target_path}\n")
            logger.info(f"Created .gitignore with: {target_path}")

    except OSError as exc:
        logger.warning(f"Failed to update .gitignore: {exc}")
        logger.info(f"Please manually add '{target_path}' to your .gitignore file.")

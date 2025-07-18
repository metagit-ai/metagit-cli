#!/usr/bin/env python
"""
Init subcommand

Used for setting up metagit for a project folder.

This command will create a .metagit.yml file in the current directory
and update the .gitignore file to include the workspace path.
"""

import os
from pathlib import Path

import click
from git import Repo

from metagit.core.appconfig import AppConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.utils.logging import UnifiedLogger
from metagit.core.utils.yaml_class import yaml


@click.command("init")
@click.option(
    "--kind",
    "-k",
    prompt="Project kind",
    default="application",
    type=click.Choice(["application", "umbrella"]),
    help="Project kind",
)
@click.option(
    "--force", "-f", is_flag=True, help="Force overwrite of existing .metagit.yml file"
)
@click.option(
    "--skip-gitignore",
    "-s",
    is_flag=True,
    help="Skip updating .gitignore file",
)
@click.pass_context
def init(ctx: click.Context, kind: str, force: bool, skip_gitignore: bool) -> None:
    """Initialize local metagit environment by creating .metagit.yml and updating .gitignore"""
    logger: UnifiedLogger = ctx.obj["logger"]
    app_config: AppConfig = ctx.obj["config"]
    current_dir = Path.cwd()
    metagit_yml_path = os.path.join(current_dir, ".metagit.yml")
    gitignore_path = os.path.join(current_dir, ".gitignore")
    workspace_path = app_config.workspace.path

    if Path(metagit_yml_path).exists() and force:
        if not click.confirm("Overwrite existing .metagit.yml?"):
            ctx.abort()

    # Check if .metagit.yml already exists
    if Path(metagit_yml_path).exists() and not force:
        logger.warning(
            "⚠️ .metagit.yml already exists, metagit_yml_path (Use --force to overwrite)"
        )
    else:
        try:
            git_repo = Repo(Path.cwd())
            name = Path(git_repo.working_dir).name
        except Exception:
            name = Path.cwd().name
        url = git_repo.remote().url or None
        # Create default .metagit.yml content
        try:
            config_file = MetagitConfig(
                name=name, description="unknown", url=url, kind=kind
            )
        except Exception as e:
            logger.error(f"❌ Failed to create config: {e}")
            ctx.abort()
        # Write .metagit.yml file
        try:
            output = yaml.safe_dump(
                config_file.model_dump(exclude_unset=False, exclude_none=True),
                default_flow_style=False,
                sort_keys=False,
                indent=2,
                line_break=True,
            )
            with open(metagit_yml_path, "w", encoding="utf-8") as f:
                f.write(output)
            logger.info(f"✅ Created .metagit.yml at {metagit_yml_path}")
        except Exception as e:
            logger.error(f"❌ Failed to create .metagit.yml: {e}")
            ctx.abort()

    # Handle .gitignore file
    if not skip_gitignore:
        _update_gitignore(gitignore_path, workspace_path, logger)
    else:
        logger.info("Skipping .gitignore file update")

    logger.header("Metagit initialization complete!")
    if kind == "application":
        logger.info("Next steps:")
        logger.info("  1. Edit .metagit.yml to configure your project manually")
        logger.info(
            "  2. Or, run 'metagit detect repo --force' to automatically discover and update your project"
        )
        logger.info(
            "  - Then, run 'metagit project sync --project local' to sync your local project"
        )
    if kind == "umbrella":
        logger.info(
            "  1. Run 'metagit project repo add' to manually a new repo to the default project"
        )
        logger.info("  2. Run 'metagit project sync' to sync the default project.")
        logger.info(
            "  3. Run 'metagit project select' to select and open the default project with your configured editor."
        )


def _sanitize_workspace_path(workspace_path: str) -> str:
    """Sanitize workspace path to ensure it is a valid path without leading ./ and with a trailing /."""
    if workspace_path.startswith("./"):
        sanitized = workspace_path[2:]
    else:
        sanitized = workspace_path

    return f"{sanitized}/" if not sanitized.endswith("/") else sanitized


def _update_gitignore(
    gitignore_path: Path, workspace_path: str, logger: UnifiedLogger
) -> None:
    """Update .gitignore file to include workspace path."""
    target_path = _sanitize_workspace_path(workspace_path)
    try:
        if Path(gitignore_path).exists():
            # Read existing .gitignore
            with open(gitignore_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Check if workspace pattern already exists by comparing each line exactly
            for line in lines:
                if line.strip() == target_path.strip():
                    logger.info(
                        f"⚠️ Workspace path already defined in .gitignore: '{target_path}'"
                    )
                    return

            # Add workspace pattern to .gitignore
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write(f"\n# Metagit workspace\n{target_path}\n")
            logger.info(f"✅ Added to existing .gitignore file: {target_path}")

        else:
            # Create new .gitignore file
            with open(gitignore_path, "w") as f:
                f.write(f"# Metagit workspace\n{target_path}\n")
            logger.info(f"✅ Created new .gitignore file: {target_path}")

    except Exception as e:
        logger.warning(f"❌ Failed to update .gitignore: {e}")
        logger.info(f"Please manually add '{target_path}' to your .gitignore file!")

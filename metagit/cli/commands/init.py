#!/usr/bin/env python
"""
Init subcommand for setting up local metagit environment.
"""

from pathlib import Path
import os
import click
import yaml

from metagit.core.utils.logging import UnifiedLogger
from metagit.core.config.manager import create_metagit_config
from metagit.core.appconfig import AppConfig


@click.command("init")

@click.option(
    "--force", "-f", is_flag=True, help="Force overwrite of existing .metagit.yml file"
)
@click.pass_context
def init(ctx: click.Context, force: bool) -> None:
    """Initialize local metagit environment by creating .metagit.yml and updating .gitignore"""
    logger: UnifiedLogger = ctx.obj["logger"]
    app_config: AppConfig = ctx.obj["config"]
    current_dir = Path.cwd()
    metagit_yml_path = os.path.join(current_dir, ".metagit.yml")
    gitignore_path = os.path.join(current_dir, ".gitignore")
    workspace_path = os.path.join(current_dir, app_config.workspace.path)
    
    # Check if .metagit.yml already exists
    if Path(metagit_yml_path).exists() and not force:
        logger.warning(f"⚠️ .metagit.yml already exists at {metagit_yml_path} (Use --force to overwrite existing file)")
    else:
      # Create default .metagit.yml content
      try:
          config_file = create_metagit_config( as_yaml=True, logger=logger )
          if isinstance(config_file, Exception):
              raise config_file
      except Exception as e:
          logger.error(f"❌ Failed to create config: {e}")
          ctx.abort()
        # Write .metagit.yml file
      try:
          with open(metagit_yml_path, 'w', encoding='utf-8') as f:
              yaml.dump(config_file, f, default_flow_style=False, sort_keys=False)
          logger.info(f"✅ Created .metagit.yml at {metagit_yml_path}")
      except Exception as e:
          logger.error(f"❌ Failed to create .metagit.yml: {e}")
          ctx.abort()

    # Handle .gitignore file
    _update_gitignore(gitignore_path, workspace_path, logger)
    
    logger.info("✅ Metagit initialization completed successfully!")
    logger.info("You can now run 'metagit detect' to analyze your project")
    logger.info("Next steps:")
    logger.info("  1. Edit .metagit.yml to configure your project")
    logger.info("  2. Run 'metagit detect' to analyze your project structure")
    logger.info("  3. Run 'metagit project sync --project local' to sync your local project")
    logger.info("Or:")
    logger.info("  1. Run 'metagit config project repo add' to manually a new repo to the default project")
    logger.info("  2. Run 'metagit config project sync' to sync the default project")


def _update_gitignore(gitignore_path: Path, workspace_path: str, logger: UnifiedLogger) -> None:
    """Update .gitignore file to include workspace path."""
    try:
        if Path(gitignore_path).exists():
            # Read existing .gitignore
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if workspace pattern already exists
            if workspace_path in content:
                logger.info(f"⚠️ Workspace path '{workspace_path}' already in .gitignore, skipping...")
                return
            
            # Add workspace pattern to .gitignore
            with open(gitignore_path, 'a', encoding='utf-8') as f:
                f.write(f"\n# Metagit workspace\n{workspace_path}\n")
            logger.info(f"✅ Added workspace path '{workspace_path}' to .gitignore")
            
        else:
            # Create new .gitignore file
            with open(gitignore_path, 'w') as f:
                f.write(f"# Metagit workspace\n{workspace_path}\n")
            logger.info(f"Created .gitignore with workspace path '{workspace_path}'")
            
    except Exception as e:
        logger.warning(f"❌ Failed to update .gitignore: {e}")
        logger.info(f"Please manually add '{workspace_path}' to your .gitignore file") 
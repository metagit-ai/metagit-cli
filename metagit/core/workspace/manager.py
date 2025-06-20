#!/usr/bin/env python
"""
Class for managing workspaces.

This package provides a class for managing workspaces.
"""

from pathlib import Path
from typing import Optional, Union

from metagit.config.models import Workspace, WorkspaceProject
from metagit.core.utils.yaml_class import yaml


def get_workspace_path(config: AppConfig) -> str:
    """
    Get the workspace path from the config.
    """
    return config.workspace.path


def get_synced_projects(config: AppConfig) -> list[WorkspaceProject]:
    """
    Get the synced projects from the config.
    """
    return config.workspace.projects


class WorkspaceManager:
    """
    Manager class for handling workspaces.

    This class provides methods for loading, validating, and creating
    workspaces with proper error handling and validation.
    """

    def __init__(self, workspace_path: str):
        """
        Initialize the MetagitWorkspaceManager.

        Args:
            workspace_path: Path to the workspace.
        """
        self.workspace_path = workspace_path
        self._workspace: Optional[Workspace] = None

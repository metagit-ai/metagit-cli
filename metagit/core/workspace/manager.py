#!/usr/bin/env python
"""
Class for managing workspaces.

This package provides a class for managing workspaces.
"""

from typing import List, Optional, Union

from metagit.core.appconfig.models import AppConfig
from metagit.core.workspace.models import Workspace, WorkspaceProject


def get_workspace_path(config: AppConfig) -> Union[str, Exception]:
    """
    Get the workspace path from the config.
    """
    try:
        return config.workspace.path
    except Exception as e:
        return e


def get_synced_projects(config: AppConfig) -> Union[List[WorkspaceProject], Exception]:
    """
    Get the synced projects from the config.
    """
    try:
        return config.workspace.projects
    except Exception as e:
        return e


class WorkspaceManager:
    """
    Manager class for handling workspaces.

    This class provides methods for loading, validating, and creating
    workspaces with proper error handling and validation.
    """

    def __init__(self, workspace_path: str) -> None:
        """
        Initialize the MetagitWorkspaceManager.

        Args:
            workspace_path: Path to the workspace.
        """
        self.workspace_path = workspace_path
        self._workspace: Optional[Workspace] = None

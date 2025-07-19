#!/usr/bin/env python
"""
Class for managing .metagit.yml configuration files.

This package provides a class for managing .metagit.yml configuration files.
"""

from pathlib import Path
from typing import Optional, Union

from git import Repo

from metagit.core.config.models import MetagitConfig
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger
from metagit.core.utils.yaml_class import yaml
from metagit.core.workspace.models import Workspace, WorkspaceProject


class MetagitConfigManager:
    """
    Manager class for handling .metagit.yml configuration files.

    This class provides methods for loading, validating, and creating
    .metagit.yml configuration files with proper error handling and validation.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        metagit_config: Optional[MetagitConfig] = None,
    ):
        """
        Initialize the MetagitConfigManager.

        Args:
            config_path: Path to the .metagit.yml file. If None, defaults to .metagit.yml in current directory.
        """
        self.config_path: str = config_path or Path(".metagit.yml")
        self._config: Optional[MetagitConfig] = metagit_config

    @property
    def config(self) -> Union[MetagitConfig, None, Exception]:
        """
        Get the loaded configuration.

        Returns:
            MetagitConfig: The loaded configuration, or None if not loaded
        """
        return self._config

    def load_config(self) -> Union[MetagitConfig, Exception]:
        """
        Load and validate a .metagit.yml configuration file.

        Returns:
            MetagitConfig: Validated configuration object

        Raises:
            FileNotFoundError: If the configuration file is not found
            yaml.YAMLError: If the YAML file is malformed
            ValidationError: If the configuration doesn't match the expected schema
        """
        try:
            if not Path(self.config_path).exists():
                return FileNotFoundError(
                    f"Configuration file not found: {self.config_path}"
                )

            with open(self.config_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)

            self._config = MetagitConfig(**yaml_data)
            return self._config
        except Exception as e:
            return e

    def validate_config(self) -> Union[bool, Exception]:
        """
        Validate a .metagit.yml configuration file without loading it into memory.

        Returns:
            bool: True if the configuration is valid, False otherwise
        """
        try:
            load_result = self.load_config()
            not isinstance(load_result, Exception)
        except Exception as e:
            return e

    def create_config(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        url: Optional[str] = None,
        kind: Optional[str] = None,
    ) -> Union[MetagitConfig, str, Exception]:
        """
        Create a .metagit.yml project configuration file.

        Args:
            output_path: Path where to save the configuration. If None, returns the config as string.

        Returns:
            MetagitConfig or str: The created configuration object or YAML string
        """
        try:
            workspace = None
            if kind == "umbrella":
                workspace = Workspace(
                    projects=[
                        WorkspaceProject(
                            name="default",
                            repos=[],
                        )
                    ],
                )
            project_config = MetagitConfig(
                name=name,
                description=description,
                url=url,
                kind=kind,
                workspace=workspace,
            )
            return project_config
        except Exception as e:
            return e

    def reload_config(self) -> Union[MetagitConfig, Exception]:
        """
        Reload the configuration from disk.

        Returns:
            MetagitConfig: The reloaded configuration object
        """
        self._config = None
        return self.load_config()

    def save_config(
        self, config: Optional[MetagitConfig] = None, output_path: Optional[Path] = None
    ) -> Union[None, Exception]:
        """
        Save a configuration to a YAML file.

        Args:
            config: Configuration to save. If None, uses the loaded config.
            output_path: Path where to save the configuration. If None, uses the instance config_path.
        """
        try:
            config_to_save = config or self._config
            if config_to_save is None:
                return ValueError(
                    "No configuration to save. Load a config first or provide one."
                )

            save_path = output_path or self.config_path
            with open(save_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    config_to_save.model_dump(exclude_none=True, exclude_defaults=True),
                    f,
                )
            return None
        except Exception as e:
            return e


def create_metagit_config(
    name: Optional[str] = None,
    description: Optional[str] = None,
    url: Optional[str] = None,
    kind: Optional[str] = None,
    logger: Optional[UnifiedLogger] = None,
    as_yaml: bool = False,
) -> Union[MetagitConfig, str, Exception]:
    """
    Create a top level .metagit.yml configuration file.
    """
    logger = logger or UnifiedLogger(
        LoggerConfig(log_level="INFO", minimal_console=True)
    )
    if name is None:
        try:
            git_repo = Repo(Path.cwd())
            name = Path(git_repo.working_dir).name
        except Exception:
            name = Path.cwd().name

    if description is None:
        description = git_repo.description or "No description"
    if url is None:
        url = git_repo.remote().url or None
    if kind is None:
        kind = "application"
    try:
        config_manager = MetagitConfigManager()
        config_result = config_manager.create_config(
            name=name, description=description, url=url, kind=kind
        )
        if isinstance(config_result, Exception):
            raise config_result
    except Exception as e:
        logger.error(f"Failed to create config: {e}")
        return e
    config_manager.paths = []
    config_manager.dependencies = []
    config_manager.components = []
    config_manager.workspace = Workspace(
        projects=[
            WorkspaceProject(
                name="default",
                repos=[],
            )
        ],
    )

    if as_yaml:
        yaml.Dumper.ignore_aliases = lambda *args: True  # noqa: ARG005
        output = yaml.dump(
            config_result.model_dump(exclude_unset=False, exclude_none=True),
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            line_break=True,
        )
        return output
    else:
        return config_result

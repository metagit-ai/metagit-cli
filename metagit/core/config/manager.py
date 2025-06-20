#!/usr/bin/env python
"""
Class for managing .metagit.yml configuration files.

This package provides a class for managing .metagit.yml configuration files.
"""

from pathlib import Path
from typing import Optional, Union

from metagit.core.config.models import MetagitConfig, Workspace, WorkspaceProject
from metagit.core.utils.yaml_class import yaml


class ConfigManager:
    """
    Manager class for handling .metagit.yml configuration files.

    This class provides methods for loading, validating, and creating
    .metagit.yml configuration files with proper error handling and validation.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the ConfigManager.

        Args:
            config_path: Path to the .metagit.yml file. If None, defaults to .metagit.yml in current directory.
        """
        self.config_path = config_path or Path(".metagit.yml")
        self._config: Optional[MetagitConfig] = None

    @property
    def config(self) -> Optional[MetagitConfig]:
        """
        Get the loaded configuration.

        Returns:
            MetagitConfig: The loaded configuration, or None if not loaded
        """
        return self._config

    def load_config(self) -> MetagitConfig:
        """
        Load and validate a .metagit.yml configuration file.

        Returns:
            MetagitConfig: Validated configuration object

        Raises:
            FileNotFoundError: If the configuration file is not found
            yaml.YAMLError: If the YAML file is malformed
            ValidationError: If the configuration doesn't match the expected schema
        """
        if not Path(self.config_path).exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)

        self._config = MetagitConfig(**yaml_data)
        return self._config

    def validate_config(self) -> bool:
        """
        Validate a .metagit.yml configuration file without loading it into memory.

        Returns:
            bool: True if the configuration is valid, False otherwise
        """
        try:
            self.load_config()
            return True
        except Exception:
            return False

    def create_config(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        url: Optional[str] = None,
        kind: Optional[str] = None,
    ) -> Union[MetagitConfig, str]:
        """
        Create a .metagit.yml project configuration file.

        Args:
            output_path: Path where to save the configuration. If None, returns the config as string.

        Returns:
            MetagitConfig or str: The created configuration object or YAML string
        """
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

    def reload_config(self) -> MetagitConfig:
        """
        Reload the configuration from disk.

        Returns:
            MetagitConfig: The reloaded configuration object
        """
        self._config = None
        return self.load_config()

    def save_config(
        self, config: Optional[MetagitConfig] = None, output_path: Optional[Path] = None
    ) -> None:
        """
        Save a configuration to a YAML file.

        Args:
            config: Configuration to save. If None, uses the loaded config.
            output_path: Path where to save the configuration. If None, uses the instance config_path.
        """
        config_to_save = config or self._config
        if config_to_save is None:
            raise ValueError(
                "No configuration to save. Load a config first or provide one."
            )

        save_path = output_path or self.config_path
        with open(save_path, "w", encoding="utf-8") as f:
            yaml.dump(config_to_save.model_dump(), f)

#!/usr/bin/env python
"""
Class for managing .metagit.yml configuration files.

This package provides a class for managing .metagit.yml configuration files.
"""

from pathlib import Path
from typing import Optional, Union

from git import Repo
from pydantic import ValidationError

from metagit.core.config.graph_models import graph_relationships_payload
from metagit.core.config.include_loader import (
    ManifestSourceMap,
    load_composed_manifest,
    manifest_declares_includes,
    map_validation_error,
)
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
        self.source_map: ManifestSourceMap | None = None
        self.resolved_files: list[Path] = []
        self._baseline_signatures: dict[str, str] | None = None
        self._loaded_root: str | None = None

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
            config_file = Path(self.config_path)
            if not config_file.exists():
                return FileNotFoundError(f"Configuration file not found: {self.config_path}")

            self.source_map = None
            self.resolved_files = []
            self._baseline_signatures = None
            self._loaded_root = None

            if manifest_declares_includes(config_file):
                composed = load_composed_manifest(config_file)
                if isinstance(composed, Exception):
                    return composed
                try:
                    self._config = MetagitConfig(**composed.data)
                except ValidationError as exc:
                    return map_validation_error(exc, composed.source_map)
                self.source_map = composed.source_map
                self.resolved_files = [Path(item) for item in composed.source_map.resolved_files]
                self._loaded_root = str(config_file.resolve())
                from metagit.core.config.include_writer import signatures_for

                signed = signatures_for(self._config, self.source_map)
                if isinstance(signed, Exception):
                    return signed
                _updated, signatures = signed
                self._baseline_signatures = signatures
                return self._config

            with open(self.config_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)

            self._config = MetagitConfig(**yaml_data)
            self.resolved_files = [config_file.resolve()]
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
            return not isinstance(load_result, Exception)
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
        self,
        config: Optional[MetagitConfig] = None,
        output_path: Optional[Path] = None,
        *,
        auto_format: bool = True,
    ) -> Union[None, Exception]:
        """
        Save a configuration to a YAML file.

        Args:
            config: Configuration to save. If None, uses the loaded config.
            output_path: Path where to save the configuration. If None, uses the instance config_path.
            auto_format: When True, use schema-ordered round-trip formatting.
        """
        try:
            config_to_save = config or self._config
            if config_to_save is None:
                return ValueError("No configuration to save. Load a config first or provide one.")

            save_path = Path(output_path or self.config_path)
            partitioned = self._partitioned_save_state(save_path)
            if isinstance(partitioned, Exception):
                return partitioned
            if partitioned is not None:
                source_map, baseline = partitioned
                from metagit.core.config.include_writer import save_partitioned

                saved = save_partitioned(
                    config_to_save,
                    source_map,
                    baseline,
                    auto_format=auto_format,
                )
                if isinstance(saved, Exception):
                    return saved
                updated_map, signatures = saved
                self.source_map = updated_map
                self._baseline_signatures = signatures
                self.resolved_files = [Path(item) for item in updated_map.resolved_files]
                self._loaded_root = str(save_path.resolve())
                self._config = config_to_save
                return None
            if save_path.is_file():
                # An existing file keeps its bytes; only the edited nodes are spliced.
                from metagit.core.config.yaml_save import splice_manifest_file

                spliced = splice_manifest_file(config_to_save, save_path)
                if isinstance(spliced, Exception):
                    return spliced
                if spliced is not None:
                    save_path.write_text(spliced, encoding="utf-8")
                return None
            if auto_format:
                from metagit.core.config.format_service import ConfigFormatService

                formatted = ConfigFormatService().render_metagit(config_to_save, original_text="")
                save_path.write_text(formatted, encoding="utf-8")
                return None

            payload = config_to_save.model_dump(
                exclude_none=True,
                exclude_defaults=True,
                by_alias=True,
            )
            if config_to_save.graph is not None and config_to_save.graph.relationships:
                payload.setdefault("graph", {})["relationships"] = graph_relationships_payload(
                    config_to_save.graph.relationships
                )
            with open(save_path, "w", encoding="utf-8") as f:
                yaml.dump(payload, f)
            return None
        except Exception as e:
            return e

    def _partitioned_save_state(
        self,
        save_path: Path,
    ) -> tuple[ManifestSourceMap, dict[str, str] | None] | None | Exception:
        """Return the source map to write, or None when the destination is one file."""
        if (
            self.source_map is not None
            and self._loaded_root is not None
            and save_path.resolve() == Path(self._loaded_root).resolve()
        ):
            return self.source_map, self._baseline_signatures
        if save_path.is_file() and manifest_declares_includes(save_path):
            from metagit.core.config.include_writer import load_baseline

            loaded = load_baseline(save_path)
            if isinstance(loaded, Exception):
                return loaded
            return loaded
        return None


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
    logger = logger or UnifiedLogger(LoggerConfig(log_level="INFO", minimal_console=True))
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
        config_result = config_manager.create_config(name=name, description=description, url=url, kind=kind)
        if isinstance(config_result, Exception):
            raise config_result
    except Exception as e:
        logger.error(f"Failed to create config: {e}")
        return e
    config_manager.paths = []
    config_manager.dependencies = []
    config_manager.components = []

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

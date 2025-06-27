#!/usr/bin/env python3

import enum
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

import yaml
from pydantic import BaseModel, Field

from metagit.core.config.models import Language
from metagit.core.detect.repository import RepositoryAnalysis
from metagit.core.record.models import MetagitRecord
from metagit.core.utils.logging import LoggingModel, UnifiedLogger


class DetectionManagerConfig(BaseModel):
    """
    Configuration for DetectionManager specifying which analysis methods are enabled.
    """

    branch_analysis_enabled: bool = Field(
        default=True, description="Enable Git branch analysis"
    )
    ci_config_analysis_enabled: bool = Field(
        default=True, description="Enable CI/CD configuration analysis"
    )
    directory_summary_enabled: bool = Field(
        default=True, description="Enable directory summary analysis"
    )
    directory_details_enabled: bool = Field(
        default=True, description="Enable detailed directory analysis"
    )
    # Future analysis methods
    commit_analysis_enabled: bool = Field(
        default=False, description="Enable Git commit analysis"
    )
    tag_analysis_enabled: bool = Field(
        default=False, description="Enable Git tag analysis"
    )

    @classmethod
    def all_enabled(cls) -> "DetectionManagerConfig":
        """Create a configuration with all analysis methods enabled."""
        return cls(
            branch_analysis_enabled=True,
            ci_config_analysis_enabled=True,
            directory_summary_enabled=True,
            directory_details_enabled=True,
            commit_analysis_enabled=True,
            tag_analysis_enabled=True,
        )

    @classmethod
    def minimal(cls) -> "DetectionManagerConfig":
        """Create a configuration with only essential analysis methods enabled."""
        return cls(
            branch_analysis_enabled=True,
            ci_config_analysis_enabled=True,
            directory_summary_enabled=False,
            directory_details_enabled=False,
            commit_analysis_enabled=False,
            tag_analysis_enabled=False,
        )

    def get_enabled_methods(self) -> list[str]:
        """Get a list of enabled analysis method names."""
        enabled = []
        if self.branch_analysis_enabled:
            enabled.append("branch_analysis")
        if self.ci_config_analysis_enabled:
            enabled.append("ci_config_analysis")
        if self.directory_summary_enabled:
            enabled.append("directory_summary")
        if self.directory_details_enabled:
            enabled.append("directory_details")
        if self.commit_analysis_enabled:
            enabled.append("commit_analysis")
        if self.tag_analysis_enabled:
            enabled.append("tag_analysis")
        return enabled


class DetectionManager(MetagitRecord, LoggingModel):
    """
    Single entrypoint for performing detection analysis of a target git project or git project path.

    This class inherits from MetagitRecord and uses RepositoryAnalysis for all detection details.
    Existing metagitconfig data is loaded first if a config file exists in the project.
    """

    # Detection-specific configuration
    detection_config: DetectionManagerConfig = Field(
        default_factory=DetectionManagerConfig, description="Analysis configuration"
    )

    # Repository analysis containing all detection results
    repository_analysis: Optional[RepositoryAnalysis] = None

    # Internal tracking
    analysis_completed: bool = Field(
        default=False, description="Whether analysis has been completed"
    )
    project_path: str = Field(default="", description="Project path for analysis")

    @property
    def path(self) -> str:
        """Get the project path."""
        return self.project_path

    @path.setter
    def path(self, value: str) -> None:
        """Set the project path."""
        self.project_path = value

    @classmethod
    def from_path(
        cls,
        path: str,
        logger: Optional[UnifiedLogger] = None,
        config: Optional[DetectionManagerConfig] = None,
    ) -> Union["DetectionManager", Exception]:
        """
        Create a DetectionManager from a local path.

        Args:
            path: Path to the git repository or project directory
            logger: Logger instance to use
            config: Detection configuration

        Returns:
            DetectionManager instance or Exception
        """
        logger = logger or UnifiedLogger().get_logger()
        try:
            # Load existing metagitconfig if it exists
            existing_config = cls._load_existing_config(path)

            # Create base MetagitRecord data
            record_data = {
                "name": Path(path).name,
                "detection_timestamp": datetime.now(timezone.utc),
                "detection_source": "local",
                "detection_version": "1.0.0",
            }

            # Merge with existing config if found
            if existing_config:
                record_data.update(existing_config.model_dump(exclude_none=True))

            # Create DetectionManager instance
            manager = cls(
                **record_data,
                detection_config=config or DetectionManagerConfig(),
                project_path=path,
            )
            manager.set_logger(logger)

            return manager

        except Exception as e:
            return e

    @classmethod
    def from_url(
        cls,
        url: str,
        temp_dir: Optional[str] = None,
        logger: Optional[UnifiedLogger] = None,
        config: Optional[DetectionManagerConfig] = None,
    ) -> Union["DetectionManager", Exception]:
        """
        Create a DetectionManager from a git URL (clones the repository).

        Args:
            url: Git repository URL
            temp_dir: Temporary directory for cloning
            logger: Logger instance to use
            config: Detection configuration

        Returns:
            DetectionManager instance or Exception
        """
        logger = logger or UnifiedLogger().get_logger()
        try:
            # Use RepositoryAnalysis to clone and get basic info
            repo_analysis = RepositoryAnalysis.from_url(url, temp_dir)
            repo_analysis.set_logger(logger)
            if isinstance(repo_analysis, Exception):
                return repo_analysis

            # Create base MetagitRecord data
            record_data = {
                "name": repo_analysis.name or Path(repo_analysis.path).name,
                "url": url,
                "detection_timestamp": datetime.now(timezone.utc),
                "detection_source": "remote",
                "detection_version": "1.0.0",
            }

            # Load existing metagitconfig if it exists in the cloned repo
            existing_config = cls._load_existing_config(repo_analysis.path)
            if existing_config:
                record_data.update(
                    existing_config.model_dump(exclude_none=True, exclude_unset=True)
                )

            # Create DetectionManager instance
            manager = cls(
                **record_data,
                detection_config=config or DetectionManagerConfig(),
                repository_analysis=repo_analysis,
                project_path=repo_analysis.path,
            )
            manager.set_logger(logger)

            return manager

        except Exception as e:
            return e

    @staticmethod
    def _load_existing_config(path: str) -> Optional[MetagitRecord]:
        """
        Load existing metagitconfig data if it exists in the project.

        Args:
            path: Path to the project directory

        Returns:
            MetagitRecord if config exists, None otherwise
        """
        try:
            config_path = Path(path) / ".metagit.yml"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                # Convert to MetagitRecord
                return MetagitRecord(**data)
        except Exception:
            # Silently fail if config loading fails
            pass
        return None

    def run_all(self) -> Union[None, Exception]:
        """
        Run all enabled detection analyses using RepositoryAnalysis.

        Returns:
            None on success, Exception on failure
        """
        try:
            # Use RepositoryAnalysis if available, otherwise create one
            if not self.repository_analysis:
                self.repository_analysis = RepositoryAnalysis.from_path(
                    self.path, self.logger
                )
                if isinstance(self.repository_analysis, Exception):
                    return self.repository_analysis

            # RepositoryAnalysis now handles all the analysis internally
            # The analysis results are already available in repository_analysis

            # Update MetagitRecord fields with detection results
            self._update_metagit_record()

            self.analysis_completed = True
            return None

        except Exception as e:
            return e

    def run_specific(self, method_name: str) -> Union[None, Exception]:
        """
        Run a specific analysis method by name.

        Note: This method now delegates to RepositoryAnalysis which runs all analyses together.
        Individual method control is handled through the detection_config.

        Args:
            method_name: Name of the analysis method to run

        Returns:
            None on success, Exception on failure
        """
        try:
            # Check if the method is enabled in config
            if (
                method_name == "branch_analysis"
                and not self.detection_config.branch_analysis_enabled
            ) or (
                method_name == "ci_config_analysis"
                and not self.detection_config.ci_config_analysis_enabled
            ) or (
                method_name == "directory_summary"
                and not self.detection_config.directory_summary_enabled
            ) or (
                method_name == "directory_details"
                and not self.detection_config.directory_details_enabled
            ):
                return Exception(f"Analysis method disabled: {method_name}")
            elif method_name not in [
                "branch_analysis",
                "ci_config_analysis",
                "directory_summary",
                "directory_details",
            ]:
                return Exception(f"Unknown analysis method: {method_name}")

            # Run all analysis (RepositoryAnalysis handles all methods together)
            return self.run_all()

        except Exception as e:
            return e

    def _update_metagit_record(self) -> None:
        """Update MetagitRecord fields with detection results from RepositoryAnalysis."""
        try:
            if not self.repository_analysis:
                return

            # Update basic fields from repository analysis
            if not self.name:
                self.name = self.repository_analysis.name
            if not self.description:
                self.description = self.repository_analysis.description
            if not self.url:
                self.url = self.repository_analysis.url

            # Update language detection
            if self.repository_analysis.language_detection:
                self.language = Language(
                    primary=self.repository_analysis.language_detection.primary,
                    secondary=getattr(
                        self.repository_analysis.language_detection,
                        "secondary",
                        None,
                    ),
                )
                self.language_version = getattr(
                    self.repository_analysis.language_detection,
                    "primary_version",
                    None,
                )

            # Update project type detection
            if self.repository_analysis.project_type_detection:
                self.kind = self.repository_analysis.project_type_detection.type
                self.domain = self.repository_analysis.project_type_detection.domain

            # Update branch information
            if self.repository_analysis.branch_analysis:
                self.branches = self.repository_analysis.branch_analysis.branches
                self.branch_strategy = (
                    self.repository_analysis.branch_analysis.strategy_guess
                )

            # Update CI/CD information
            if self.repository_analysis.ci_config_analysis:
                from metagit.core.config.models import CICD, Pipeline

                pipelines = []
                for tool in self.repository_analysis.ci_config_analysis.detected_tools:
                    pipelines.append(Pipeline(name=tool, ref=f".{tool}"))

                self.cicd = CICD(
                    platform=self.repository_analysis.ci_config_analysis.detected_tool,
                    pipelines=pipelines,
                )

            # Update metrics
            if self.repository_analysis.metrics:
                self.metrics = self.repository_analysis.metrics

            # Update metadata
            if self.repository_analysis.metadata:
                self.metadata = self.repository_analysis.metadata

            # Update license information
            if self.repository_analysis.license_info:
                self.license = self.repository_analysis.license_info

            # Update maintainers
            if self.repository_analysis.maintainers:
                self.maintainers = self.repository_analysis.maintainers

            # Update artifacts
            if self.repository_analysis.artifacts:
                self.artifacts = self.repository_analysis.artifacts

            # Update secrets management
            if self.repository_analysis.secrets_management:
                self.secrets_management = self.repository_analysis.secrets_management

            # Update secrets
            if self.repository_analysis.secrets:
                self.secrets = self.repository_analysis.secrets

            # Update documentation
            if self.repository_analysis.documentation:
                self.documentation = self.repository_analysis.documentation

            # Update observability information
            observability_data = {}
            if self.repository_analysis.alerts:
                observability_data["alerting_channels"] = (
                    self.repository_analysis.alerts
                )
            if self.repository_analysis.dashboards:
                observability_data["dashboards"] = self.repository_analysis.dashboards

            if observability_data:
                from metagit.core.config.models import Observability

                self.observability = Observability(**observability_data)

            # Update deployment information
            deployment_data = {}
            if self.repository_analysis.environments:
                deployment_data["environments"] = self.repository_analysis.environments

            if deployment_data:
                from metagit.core.config.models import Deployment

                self.deployment = Deployment(**deployment_data)

        except Exception as e:
            self.logger.warning(f"Failed to update MetagitRecord: {e}")

    def summary(self) -> Union[str, Exception]:
        """
        Generate a summary of the detection results.

        Returns:
            Summary string or Exception
        """
        try:
            lines = [f"Detection Analysis for: {self.name or self.path}"]
            lines.append(f"Path: {self.path}")
            if self.url:
                lines.append(f"URL: {self.url}")
            lines.append(f"Detection completed: {self.analysis_completed}")
            lines.append(
                f"Enabled methods: {', '.join(self.detection_config.get_enabled_methods())}"
            )

            # MetagitRecord summary
            if self.kind:
                lines.append(f"Project type: {self.kind}")
            if self.domain:
                lines.append(f"Domain: {self.domain}")
            if self.language:
                lines.append(f"Primary language: {self.language}")
            if self.branch_strategy:
                lines.append(f"Branch strategy: {self.branch_strategy}")

            # Detection results summary from RepositoryAnalysis
            if self.repository_analysis:
                # Branch analysis
                if self.repository_analysis.branch_analysis:
                    lines.append(
                        f"Branching strategy: {self.repository_analysis.branch_analysis.strategy_guess}"
                    )
                    lines.append("Branches:")
                    for b in self.repository_analysis.branch_analysis.branches:
                        lines.append(
                            f"  - {'[remote]' if b.is_remote else '[local]'} {b.name}"
                        )
                elif self.detection_config.branch_analysis_enabled:
                    lines.append("Branch analysis not available.")

                # CI/CD analysis
                if self.repository_analysis.ci_config_analysis:
                    lines.append(
                        f"CI/CD tool: {self.repository_analysis.ci_config_analysis.detected_tool}"
                    )
                elif self.detection_config.ci_config_analysis_enabled:
                    lines.append("CI/CD analysis not available.")

                # Directory analysis
                if self.repository_analysis.directory_summary:
                    lines.append(
                        f"Directory summary: {self.repository_analysis.directory_summary.num_files} files, {len(self.repository_analysis.directory_summary.file_types)} file types"
                    )
                elif self.detection_config.directory_summary_enabled:
                    lines.append("Directory summary not available.")

                if self.repository_analysis.directory_details:
                    total_categories = len(
                        self.repository_analysis.directory_details.file_types
                    )
                    lines.append(
                        f"Directory details: {self.repository_analysis.directory_details.num_files} files, {total_categories} file type categories"
                    )
                elif self.detection_config.directory_details_enabled:
                    lines.append("Directory details not available.")

            return "\n".join(lines)
        except Exception as e:
            return e

    def remove_logger(self, obj: Any) -> Union[Any, Exception]:
        """Recursively remove logger from objects for serialization, including nested Pydantic models."""
        try:
            from pydantic import BaseModel

            if isinstance(obj, dict):
                return {
                    k: self.remove_logger(v) for k, v in obj.items() if k != "logger"
                }
            elif isinstance(obj, list):
                return [self.remove_logger(item) for item in obj]
            elif hasattr(obj, "_asdict"):  # NamedTuple
                return self.remove_logger(obj._asdict())
            elif isinstance(obj, BaseModel):
                # Convert to dict, excluding logger, and recurse
                return self.remove_logger(obj.model_dump(exclude={"logger"}))
            else:
                return obj
        except Exception as e:
            return e

    def to_yaml(self) -> Union[str, Exception]:
        """
        Convert the DetectionManager model to a YAML string.
        """
        try:
            # Use pydantic's .model_dump() for dict conversion (v2+), else .dict()
            data = (
                self.model_dump(exclude={"logger", "detection_config"})
                if hasattr(self, "model_dump")
                else dict(self, exclude={"logger", "detection_config"})
            )
            data = self.remove_logger(data)
            if isinstance(data, Exception):
                return data
            # Extra safety: remove logger at the top level if present
            data.pop("logger", None)

            # Convert Enums to their values and NamedTuples to dicts
            def convert_objects(obj):
                if isinstance(obj, enum.Enum):
                    return obj.value
                elif hasattr(
                    obj, "_asdict"
                ):  # NamedTuple (including DirectoryDetails, FileTypeWithPercent)
                    result = obj._asdict()
                    # Recursively convert nested objects
                    for key, value in result.items():
                        result[key] = convert_objects(value)
                    return result
                elif isinstance(obj, dict):
                    return {k: convert_objects(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_objects(item) for item in obj]
                elif hasattr(obj, "__dict__") and not isinstance(
                    obj, (str, int, float, bool, type(None))
                ):
                    obj_dict = obj.__dict__.copy()
                    for key, value in obj_dict.items():
                        obj_dict[key] = convert_objects(value)
                    return obj_dict
                else:
                    return obj

            data = convert_objects(data)

            # Handle RepositoryAnalysis serialization
            if "repository_analysis" in data and data["repository_analysis"]:
                # Convert RepositoryAnalysis to a serializable format
                repo_data = data["repository_analysis"]
                if hasattr(repo_data, "model_dump"):
                    data["repository_analysis"] = convert_objects(
                        repo_data.model_dump()
                    )

            return yaml.safe_dump(data, sort_keys=False, default_flow_style=False)
        except Exception as e:
            return e

    def to_json(self) -> Union[str, Exception]:
        """
        Convert the DetectionManager model to a JSON string.
        """
        try:
            data = (
                self.model_dump(exclude={"logger", "detection_config"})
                if hasattr(self, "model_dump")
                else dict(self, exclude={"logger", "detection_config"})
            )
            data = self.remove_logger(data)
            if isinstance(data, Exception):
                return data
            # Extra safety: remove logger at the top level if present
            data.pop("logger", None)

            # Convert datetime objects to ISO format strings and NamedTuples to dicts for JSON serialization
            def convert_objects(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif hasattr(obj, "_asdict"):  # NamedTuple
                    result = obj._asdict()
                    # Recursively convert nested objects
                    for key, value in result.items():
                        if isinstance(value, list):
                            result[key] = [convert_objects(item) for item in value]
                        elif isinstance(value, dict):
                            result[key] = {
                                k: convert_objects(v) for k, v in value.items()
                            }
                        elif hasattr(value, "_asdict"):
                            result[key] = convert_objects(value)
                    return result
                elif isinstance(obj, dict):
                    return {k: convert_objects(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_objects(item) for item in obj]
                elif hasattr(obj, "__dict__") and not isinstance(
                    obj, (str, int, float, bool, type(None))
                ):
                    obj_dict = obj.__dict__.copy()
                    for key, value in obj_dict.items():
                        obj_dict[key] = convert_objects(value)
                    return obj_dict
                else:
                    return obj

            data = convert_objects(data)

            # Handle RepositoryAnalysis serialization
            if "repository_analysis" in data and data["repository_analysis"]:
                # Convert RepositoryAnalysis to a serializable format
                repo_data = data["repository_analysis"]
                if hasattr(repo_data, "model_dump"):
                    data["repository_analysis"] = convert_objects(
                        repo_data.model_dump()
                    )

            return json.dumps(data, indent=2, default=str)
        except Exception as e:
            return e

    def cleanup(self) -> None:
        """Clean up temporary files if this was a cloned repository."""
        if self.repository_analysis:
            self.repository_analysis.cleanup()

#!/usr/bin/env python3

import enum
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

import yaml
from pydantic import BaseModel, Field

from metagit.core.config.models import Branch, Language, MetagitRecord
from metagit.core.detect.branch import GitBranchAnalysis
from metagit.core.detect.cicd import CIConfigAnalysis
from metagit.core.detect.repository import RepositoryAnalysis
from metagit.core.utils.files import (
    DirectoryDetails,
    DirectorySummary,
    FileExtensionLookup,
    directory_details,
    directory_summary,
)
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

    This class inherits from MetagitRecord and includes all detection details while maintaining
    the RepositoryAnalysis features where possible. Existing metagitconfig data is loaded first
    if a config file exists in the project.
    """

    # Detection-specific configuration
    detection_config: DetectionManagerConfig = Field(
        default_factory=DetectionManagerConfig, description="Analysis configuration"
    )

    # Detection analysis results
    branch_analysis: Optional[GitBranchAnalysis] = None
    ci_config_analysis: Optional[CIConfigAnalysis] = None
    directory_summary: Optional[DirectorySummary] = None
    directory_details: Optional[DirectoryDetails] = None
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
        Run all enabled detection analyses.

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

            # Run individual analyses based on configuration
            if self.detection_config.branch_analysis_enabled:
                self.branch_analysis = GitBranchAnalysis.from_repo(
                    self.path, self.logger
                )

            if self.detection_config.ci_config_analysis_enabled:
                self.ci_config_analysis = CIConfigAnalysis.from_repo(
                    self.path, self.logger
                )

            if self.detection_config.directory_summary_enabled:
                self.directory_summary = directory_summary(self.path)

            if self.detection_config.directory_details_enabled:
                file_lookup = FileExtensionLookup()
                self.directory_details = directory_details(self.path, file_lookup)

            # Update MetagitRecord fields with detection results
            self._update_metagit_record()

            self.analysis_completed = True
            return None

        except Exception as e:
            return e

    def run_specific(self, method_name: str) -> Union[None, Exception]:
        """
        Run a specific analysis method by name.

        Args:
            method_name: Name of the analysis method to run

        Returns:
            None on success, Exception on failure
        """
        try:
            if (
                method_name == "branch_analysis"
                and self.detection_config.branch_analysis_enabled
            ):
                self.branch_analysis = GitBranchAnalysis.from_repo(
                    self.path, self.logger
                )
            elif (
                method_name == "ci_config_analysis"
                and self.detection_config.ci_config_analysis_enabled
            ):
                self.ci_config_analysis = CIConfigAnalysis.from_repo(
                    self.path, self.logger
                )
            elif (
                method_name == "directory_summary"
                and self.detection_config.directory_summary_enabled
            ):
                self.directory_summary = directory_summary(self.path)
            elif (
                method_name == "directory_details"
                and self.detection_config.directory_details_enabled
            ):
                file_lookup = FileExtensionLookup()
                self.directory_details = directory_details(self.path, file_lookup)
            else:
                return Exception(f"Unknown or disabled analysis method: {method_name}")

            # Update MetagitRecord fields
            self._update_metagit_record()
            return None

        except Exception as e:
            return e

    def _update_metagit_record(self) -> None:
        """Update MetagitRecord fields with detection results."""
        try:
            # Update basic fields from repository analysis
            if self.repository_analysis:
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

                # Update project type - convert ProjectType to ProjectKind
                if self.repository_analysis.project_type_detection:
                    # Map ProjectType to ProjectKind
                    project_type_to_kind = {
                        "application": "application",
                        "library": "library",
                        "cli": "cli",
                        "microservice": "service",
                        "iac": "infrastructure",
                        "config": "other",
                        "data-science": "other",
                        "plugin": "library",
                        "template": "other",
                        "docs": "website",
                        "test": "other",
                        "other": "other",
                    }

                    project_type_value = (
                        self.repository_analysis.project_type_detection.type.value
                    )
                    kind_value = project_type_to_kind.get(project_type_value, "other")

                    # Import ProjectKind here to avoid circular imports
                    from metagit.core.project.models import ProjectKind

                    self.kind = ProjectKind(kind_value)

                    # Set domain
                    self.domain = self.repository_analysis.project_type_detection.domain

                # Update metadata
                if self.repository_analysis.metadata:
                    self.metadata = self.repository_analysis.metadata

                # Update metrics
                if self.repository_analysis.metrics:
                    self.metrics = self.repository_analysis.metrics

                # Update branches
                if self.repository_analysis.branch_analysis:
                    # Convert BranchInfo to Branch objects
                    self.branches = [
                        Branch(
                            name=branch_info.name,
                            environment="remote" if branch_info.is_remote else "local",
                        )
                        for branch_info in self.repository_analysis.branch_analysis.branches
                    ]
                    if self.branches:
                        self.branch = self.branches[0].name  # Current branch

            # Update detection timestamp
            self.detection_timestamp = datetime.now(timezone.utc)

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

            # Detection results summary
            if self.branch_analysis:
                lines.append(
                    f"Branching strategy: {self.branch_analysis.strategy_guess}"
                )
                lines.append("Branches:")
                for b in self.branch_analysis.branches:
                    lines.append(
                        f"  - {'[remote]' if b.is_remote else '[local]'} {b.name}"
                    )
            elif self.detection_config.branch_analysis_enabled:
                lines.append("Branch analysis not available.")

            if self.ci_config_analysis:
                lines.append(f"CI/CD tool: {self.ci_config_analysis.detected_tool}")
            elif self.detection_config.ci_config_analysis_enabled:
                lines.append("CI/CD analysis not available.")

            if self.directory_summary:
                lines.append(
                    f"Directory summary: {self.directory_summary.num_files} files, {len(self.directory_summary.file_types)} file types"
                )
            elif self.detection_config.directory_summary_enabled:
                lines.append("Directory summary not available.")

            if self.directory_details:
                total_categories = len(self.directory_details.file_types)
                lines.append(
                    f"Directory details: {self.directory_details.num_files} files, {total_categories} file type categories"
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

            # Debug: Check what directory_details looks like
            if "directory_details" in data:
                print(
                    f"DEBUG: directory_details type: {type(data['directory_details'])}"
                )
                print(f"DEBUG: directory_details value: {data['directory_details']}")
                if hasattr(data["directory_details"], "_asdict"):
                    print("DEBUG: directory_details has _asdict method")
                    data["directory_details"] = convert_objects(
                        data["directory_details"]
                    )
                elif isinstance(data["directory_details"], tuple):
                    # Pydantic converted NamedTuple to tuple, convert back to dict with field names
                    from metagit.core.utils.files import DirectoryDetails

                    dd_fields = DirectoryDetails._fields
                    if len(data["directory_details"]) == len(dd_fields):
                        data["directory_details"] = dict(
                            zip(dd_fields, data["directory_details"])
                        )
                        # Recursively convert nested objects
                        data["directory_details"] = convert_objects(
                            data["directory_details"]
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
                    # Handle Pydantic models and other objects
                    obj_dict = obj.__dict__.copy()
                    for key, value in obj_dict.items():
                        if isinstance(value, enum.Enum):
                            obj_dict[key] = value.value
                        elif isinstance(value, (list, dict)):
                            obj_dict[key] = convert_objects(value)
                        elif hasattr(value, "__dict__") and not isinstance(
                            value, (str, int, float, bool, type(None))
                        ):
                            obj_dict[key] = convert_objects(value)
                    return obj_dict
                else:
                    return obj

            data = convert_objects(data)
            return json.dumps(data, indent=2)
        except Exception as e:
            return e

    def cleanup(self) -> None:
        """Clean up any temporary resources."""
        if self.repository_analysis and hasattr(self.repository_analysis, "cleanup"):
            self.repository_analysis.cleanup()

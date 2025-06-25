#!/usr/bin/env python3

import json
import logging
from typing import Any, Optional, Union

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from metagit.core.detect.branch import GitBranchAnalysis
from metagit.core.detect.cicd import CIConfigAnalysis
from metagit.core.utils.files import (
    DirectoryDetails,
    DirectorySummary,
    FileExtensionLookup,
    directory_details,
    directory_summary,
)
from metagit.core.utils.logging import LoggerConfig, UnifiedLogger

load_dotenv()

default_logger = UnifiedLogger(
    LoggerConfig(
        name="RepositoryAnalysis",
        level=logging.INFO,
        console=True,
        terse=False,
    )
)


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


class DetectionManager(BaseModel):
    path: str
    url: Optional[str] = None
    branch: Optional[str] = None
    checksum: Optional[Union[str, int]] = None
    content_summary: Optional[dict[str, Any]] = None
    last_updated: Optional[str] = None
    config: DetectionManagerConfig = Field(
        default_factory=DetectionManagerConfig, description="Analysis configuration"
    )
    branch_analysis: Optional[GitBranchAnalysis] = None
    ci_config_analysis: Optional[CIConfigAnalysis] = None
    directory_summary: Optional[DirectorySummary] = None
    directory_details: Optional[DirectoryDetails] = None
    logger: Optional[Any] = None
    # commit_analysis: Optional[GitCommitAnalysis] = None
    # tag_analysis: Optional[GitTagAnalysis] = None

    def model_post_init(self, __context: Any) -> None:
        # Use provided logger or fallback to top-level default_logger
        self.logger = self.logger or default_logger

    def run_all(self) -> Union[None, Exception]:
        try:
            if self.config.branch_analysis_enabled:
                self.branch_analysis = GitBranchAnalysis.from_repo(
                    self.path, self.logger
                )

            if self.config.ci_config_analysis_enabled:
                self.ci_config_analysis = CIConfigAnalysis.from_repo(
                    self.path, self.logger
                )

            if self.config.directory_summary_enabled:
                self.directory_summary = directory_summary(self.path)

            if self.config.directory_details_enabled:
                file_lookup = FileExtensionLookup()
                self.directory_details = directory_details(self.path, file_lookup)

            # Future calls:
            # if self.config.commit_analysis_enabled:
            #     self.commit_analysis = GitCommitAnalysis.from_repo(self.path)
            # if self.config.tag_analysis_enabled:
            #     self.tag_analysis = GitTagAnalysis.from_repo(self.path)

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
            if method_name == "branch_analysis" and self.config.branch_analysis_enabled:
                self.branch_analysis = GitBranchAnalysis.from_repo(
                    self.path, self.logger
                )
            elif (
                method_name == "ci_config_analysis"
                and self.config.ci_config_analysis_enabled
            ):
                self.ci_config_analysis = CIConfigAnalysis.from_repo(
                    self.path, self.logger
                )
            elif (
                method_name == "directory_summary"
                and self.config.directory_summary_enabled
            ):
                self.directory_summary = directory_summary(self.path)
            elif (
                method_name == "directory_details"
                and self.config.directory_details_enabled
            ):
                file_lookup = FileExtensionLookup()
                self.directory_details = directory_details(self.path, file_lookup)
            # elif method_name == "commit_analysis" and self.config.commit_analysis_enabled:
            #     self.commit_analysis = GitCommitAnalysis.from_repo(self.path)
            # elif method_name == "tag_analysis" and self.config.tag_analysis_enabled:
            #     self.tag_analysis = GitTagAnalysis.from_repo(self.path)
            else:
                return Exception(f"Unknown or disabled analysis method: {method_name}")

            return None
        except Exception as e:
            return e

    def summary(self) -> Union[str, Exception]:
        try:
            lines = [f"Analysis for project at: {self.path}"]
            lines.append(
                f"Enabled methods: {', '.join(self.config.get_enabled_methods())}"
            )

            if self.branch_analysis:
                lines.append(
                    f"Branching strategy: {self.branch_analysis.strategy_guess}"
                )
                lines.append("Branches:")
                for b in self.branch_analysis.branches:
                    lines.append(
                        f"  - {'[remote]' if b.is_remote else '[local]'} {b.name}"
                    )
            elif self.config.branch_analysis_enabled:
                lines.append("Branch analysis not available.")

            if self.ci_config_analysis:
                lines.append(f"CI/CD tool: {self.ci_config_analysis.detected_tool}")
            elif self.config.ci_config_analysis_enabled:
                lines.append("CI/CD analysis not available.")

            if self.directory_summary:
                lines.append(
                    f"Directory summary: {self.directory_summary.num_files} files, {len(self.directory_summary.file_types)} file types"
                )
            elif self.config.directory_summary_enabled:
                lines.append("Directory summary not available.")

            if self.directory_details:
                total_categories = len(self.directory_details.file_types)
                lines.append(
                    f"Directory details: {self.directory_details.num_files} files, {total_categories} file type categories"
                )
            elif self.config.directory_details_enabled:
                lines.append("Directory details not available.")

            return "\n".join(lines)
        except Exception as e:
            return e

    def remove_logger(self, obj: Any) -> Union[Any, Exception]:
        try:
            if isinstance(obj, dict):
                return {
                    k: self.remove_logger(v) for k, v in obj.items() if k != "logger"
                }
            elif isinstance(obj, list):
                return [self.remove_logger(item) for item in obj]
            else:
                return obj
        except Exception as e:
            return e

    def to_yaml(self) -> Union[str, Exception]:
        """
        Convert the DetectionManager model (including all nested models) to a YAML string.
        """
        try:
            # Use pydantic's .model_dump() for dict conversion (v2+), else .dict()
            data = (
                self.model_dump(exclude={"logger", "config"})
                if hasattr(self, "model_dump")
                else dict(self, exclude={"logger", "config"})
            )
            data = self.remove_logger(data)
            if isinstance(data, Exception):
                return data
            return yaml.safe_dump(data, sort_keys=False, default_flow_style=False)
        except Exception as e:
            return e

    def to_json(self) -> Union[str, Exception]:
        """
        Convert the DetectionManager model (including all nested models) to a JSON string.
        """
        try:
            data = (
                self.model_dump(exclude={"logger", "config"})
                if hasattr(self, "model_dump")
                else dict(self, exclude={"logger", "config"})
            )
            data = self.remove_logger(data)
            if isinstance(data, Exception):
                return data
            return json.dumps(data, indent=4)
        except Exception as e:
            return e

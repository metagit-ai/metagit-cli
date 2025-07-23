#!/usr/bin/env python3
"""
Combined models for the detect module.

This module contains all the Pydantic models used in the detection system,
including language detection, project type detection, branch analysis, CI/CD analysis,
and detection manager configuration.
"""

import os
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from metagit import DATA_PATH
from metagit.core.config.models import ProjectDomain, ProjectType
from metagit.core.utils.logging import LoggingModel


class LanguageDetection(BaseModel):
    """Model for language detection results."""

    primary: str = Field(default="Unknown", description="Primary programming language")
    secondary: List[str] = Field(
        default_factory=list, description="Secondary programming languages"
    )
    frameworks: List[str] = Field(
        default_factory=list, description="Detected frameworks"
    )
    package_managers: List[str] = Field(
        default_factory=list, description="Detected package managers"
    )
    build_tools: List[str] = Field(
        default_factory=list, description="Detected build tools"
    )

    class Config:
        use_enum_values = True
        extra = "forbid"


class ProjectTypeDetection(BaseModel):
    """Model for project type detection results."""

    type: ProjectType = Field(
        default=ProjectType.OTHER, description="Detected project type"
    )
    domain: ProjectDomain = Field(
        default=ProjectDomain.OTHER, description="Detected project domain"
    )
    confidence: float = Field(default=0.0, description="Confidence score (0.0 to 1.0)")
    indicators: List[str] = Field(
        default_factory=list, description="Indicators used for detection"
    )

    class Config:
        use_enum_values = True
        extra = "forbid"


class BranchInfo(BaseModel):
    """Model for branch information."""

    name: str = Field(..., description="Branch name")
    is_remote: bool = Field(
        default=False, description="Whether this is a remote branch"
    )


class BranchStrategy(str, Enum):
    """Model for branch strategy."""

    GIT_FLOW = "Git Flow"
    GITHUB_FLOW = "GitHub Flow"
    GITLAB_FLOW = "GitLab Flow"
    TRUNK_BASED_DEVELOPMENT = "Trunk-Based Development"
    RELEASE_BRANCHING = "Release Branching"
    UNKNOWN = "Unknown"
    OTHER = "Other"


class GitBranchAnalysis(LoggingModel):
    """Model for Git branch analysis results."""

    branches: List[BranchInfo] = Field(
        default_factory=list, description="List of branches"
    )
    strategy_guess: Optional[BranchStrategy] = Field(
        default=BranchStrategy.UNKNOWN, description="Detected branching strategy"
    )

    class Config:
        use_enum_values = True
        extra = "forbid"

    # @classmethod
    # def from_repo(
    #     cls, repo_path: str = ".", logger: Optional[UnifiedLogger] = None
    # ) -> Union["GitBranchAnalysis", Exception]:
    #     """
    #     Analyze the git repository at the given path and return branch information and a strategy guess.
    #     Uses GitPython for all git operations.
    #     """
    #     logger = logger or UnifiedLogger().get_logger()

    #     try:
    #         repo = Repo(repo_path)
    #     except (InvalidGitRepositoryError, NoSuchPathError) as e:
    #         logger.exception(f"Invalid git repository at '{repo_path}': {e}")
    #         return ValueError(f"Invalid git repository at '{repo_path}': {e}")

    #     # Get local branches
    #     local_branches = [
    #         BranchInfo(name=branch.name, is_remote=False)
    #         for branch in repo.branches
    #         if branch.name != "HEAD"  # Exclude HEAD branch
    #     ]
    #     logger.debug(f"Found {len(local_branches)} local branches")

    #     # Get remote branches
    #     remote_branches = []
    #     for remote in repo.remotes:
    #         for ref in remote.refs:
    #             # Remove remote name prefix (e.g., 'origin/')
    #             branch_name = ref.name.split("/", 1)[1] if "/" in ref.name else ref.name
    #             # Exclude HEAD branch from remote branches
    #             if branch_name != "HEAD":
    #                 remote_branches.append(BranchInfo(name=branch_name, is_remote=True))
    #     logger.debug(f"Found {len(remote_branches)} remote branches")

    #     # Combine and deduplicate branches (prefer local if name overlaps)
    #     all_branches_dict = {b.name: b for b in remote_branches}
    #     all_branches_dict.update({b.name: b for b in local_branches})
    #     all_branches = list(all_branches_dict.values())

    #     # Analyze branching strategy
    #     strategy_guess = cls._analyze_branching_strategy(all_branches, logger)

    #     return cls(branches=all_branches, strategy_guess=strategy_guess)

    # @staticmethod
    # def _analyze_branching_strategy(
    #     branches: List[BranchInfo], logger: UnifiedLogger
    # ) -> str:
    #     """Analyze the branching strategy based on branch names and patterns."""
    #     branch_names = [b.name for b in branches]
    #     local_branches = [b.name for b in branches if not b.is_remote]

    #     logger.debug(f"Analyzing branching strategy for branches: {branch_names}")

    #     # Check for Git Flow patterns
    #     if any(name in branch_names for name in ["develop", "master", "main"]):
    #         if "develop" in branch_names:
    #             return "Git Flow"

    #     # Check for GitHub Flow patterns
    #     if "main" in branch_names or "master" in branch_names:
    #         if len(local_branches) <= 2:  # main/master + feature branches
    #             return "GitHub Flow"

    #     # Check for GitLab Flow patterns
    #     if any(name in branch_names for name in ["staging", "production"]):
    #         return "GitLab Flow"

    #     # Check for Trunk-Based Development
    #     if len(local_branches) <= 1:
    #         return "Trunk-Based Development"

    #     # Check for Release Branching
    #     if any(name.startswith("release/") for name in branch_names):
    #         return "Release Branching"

    #     return "Unknown"


class CIConfigAnalysis(LoggingModel):
    """Model for CI/CD configuration analysis results."""

    detected_tool: Optional[str] = Field(None, description="Detected CI/CD tool")
    ci_config_path: Optional[str] = Field(
        None, description="Path to CI/CD configuration file"
    )
    config_content: Optional[str] = Field(
        None, description="Content of CI/CD configuration file"
    )
    pipeline_count: int = Field(default=0, description="Number of detected pipelines")
    triggers: Optional[List[str]] = Field(default=[], description="Detected triggers")

    # @classmethod
    # def from_repo(
    #     cls, repo_path: str = ".", logger: Optional[UnifiedLogger] = None
    # ) -> Union["CIConfigAnalysis", Exception]:
    #     """
    #     Analyze CI/CD configuration in the repository.

    #     Args:
    #         repo_path: Path to the repository
    #         logger: Logger instance

    #     Returns:
    #         CIConfigAnalysis object or Exception
    #     """
    #     logger = logger or UnifiedLogger().get_logger()

    #     try:
    #         repo_path_obj = Path(repo_path)
    #         analysis = cls()

    #         # Check for common CI/CD configuration files
    #         ci_files = {
    #             ".github/workflows/": "GitHub Actions",
    #             ".gitlab-ci.yml": "GitLab CI",
    #             ".circleci/config.yml": "CircleCI",
    #             "Jenkinsfile": "Jenkins",
    #             ".travis.yml": "Travis CI",
    #             "azure-pipelines.yml": "Azure DevOps",
    #             "bitbucket-pipelines.yml": "Bitbucket Pipelines",
    #         }

    #         for file_path, tool_name in ci_files.items():
    #             full_path = os.path.join(repo_path_obj, file_path)
    #             if full_path.exists():
    #                 analysis.detected_tool = tool_name
    #                 analysis.ci_config_path = str(full_path)

    #                 # Read configuration content
    #                 if full_path.is_dir():
    #                     for file in full_path.iterdir():
    #                         if file.is_file():
    #                             with open(file, "r", encoding="utf-8") as f:
    #                                 analysis.config_content = f.read()
    #                 else:
    #                     try:
    #                         with open(full_path, "r", encoding="utf-8") as f:
    #                             analysis.config_content = f.read()
    #                     except Exception as e:
    #                         logger.warning(
    #                             f"Could not read CI config file {full_path}: {e}"
    #                         )

    #                 logger.debug(f"Detected CI/CD tool: {tool_name}")
    #                 break

    #         # Count pipelines (basic heuristic)
    #         if analysis.config_content:
    #             # Simple pipeline counting based on common patterns
    #             pipeline_indicators = ["job:", "stage:", "pipeline:", "workflow:"]
    #             analysis.pipeline_count = sum(
    #                 1
    #                 for indicator in pipeline_indicators
    #                 if indicator in analysis.config_content
    #             )

    #         return analysis

    #     except Exception as e:
    #         logger.exception(f"CI/CD analysis failed: {e}")
    #         return e


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
    data_file_type_source: Optional[str] = Field(
        default=os.path.join(DATA_PATH, "file-types.json"),
        description="Source of data file types",
    )
    data_ci_file_source: Optional[str] = Field(
        default=os.path.join(DATA_PATH, "ci-files.json"),
        description="Source of data CI files",
    )
    data_cd_file_source: Optional[str] = Field(
        default=os.path.join(DATA_PATH, "cd-files.json"),
        description="Source of data CD files",
    )
    data_package_manager_source: Optional[str] = Field(
        default=os.path.join(DATA_PATH, "package-managers.json"),
        description="Source of data package managers",
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

#!/usr/bin/env python3

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Union

import yaml
from git import InvalidGitRepositoryError, NoSuchPathError, Repo
from pydantic import Field

from metagit.core.config.models import (
    Branch,
    Language,
    MetagitConfig,
    Metrics,
    PullRequests,
    RepoMetadata,
)
from metagit.core.detect.models import (
    BranchInfo,
    BranchStrategy,
    CIConfigAnalysis,
    DetectionManagerConfig,
    GitBranchAnalysis,
    LanguageDetection,
    ProjectTypeDetection,
)
from metagit.core.record.models import MetagitRecord
from metagit.core.utils.common import normalize_git_url
from metagit.core.utils.files import (
    FileExtensionLookup,
    directory_details,
    directory_summary,
)
from metagit.core.utils.logging import LoggerConfig, LoggingModel, UnifiedLogger


class DetectionManager(MetagitRecord, LoggingModel):
    """
    Single entrypoint for performing detection analysis of a target git project or git project path.

    This class inherits from MetagitRecord and includes all RepositoryAnalysis functionality.
    Existing metagitconfig data is loaded first if a config file exists in the project.
    """

    # Detection-specific configuration
    detection_config: DetectionManagerConfig = Field(
        default_factory=DetectionManagerConfig, description="Analysis configuration"
    )

    # Internal tracking
    analysis_completed: bool = Field(
        default=False, description="Whether analysis has been completed"
    )

    @property
    def project_path(self) -> str:
        """Get the project path."""
        return self.path or ""

    @project_path.setter
    def project_path(self, value: str) -> None:
        """Set the project path."""
        self.path = value

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
        logger = logger or UnifiedLogger(LoggerConfig()).get_logger()
        try:
            logger.debug(f"Creating DetectionManager from path: {path}")

            if not os.path.exists(path):
                return FileNotFoundError(f"Path does not exist: {path}")

            # Load existing metagitconfig if it exists
            existing_config = cls._load_existing_config(path)

            # Create base MetagitRecord data
            record_data = {
                "name": Path(path).name,
                "path": path,
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
        logger = logger or UnifiedLogger(LoggerConfig()).get_logger()
        try:
            normalized_url = normalize_git_url(url)
            logger.debug(f"Creating DetectionManager from URL: {normalized_url}")

            # Create temporary directory if not provided
            if temp_dir is None:
                temp_dir = tempfile.mkdtemp(prefix="metagit_")

            # Clone the repository
            try:
                _ = Repo.clone_from(normalized_url, temp_dir)
                logger.debug(f"Successfully cloned repository to: {temp_dir}")
            except Exception as e:
                return Exception(f"Failed to clone repository: {e}")

            # Create base MetagitRecord data
            record_data = {
                "name": Path(temp_dir).name,
                "path": temp_dir,
                "url": normalized_url,
                "is_git_repo": True,
                "is_cloned": True,
                "temp_dir": temp_dir,
                "detection_timestamp": datetime.now(timezone.utc),
                "detection_source": "remote",
                "detection_version": "1.0.0",
            }

            # Load existing metagitconfig if it exists in the cloned repo
            existing_config = cls._load_existing_config(temp_dir)
            if existing_config:
                record_data.update(existing_config.model_dump(exclude_none=True))

            # Create DetectionManager instance
            manager = cls(
                **record_data,
                detection_config=config or DetectionManagerConfig(),
            )
            manager.set_logger(logger)

            return manager

        except Exception as e:
            return e

    @staticmethod
    def _load_existing_config(path: str) -> Optional[MetagitConfig]:
        """Load existing metagitconfig if it exists in the project."""
        config_paths = [
            Path(path) / "metagit.config.yaml",
            Path(path) / "metagit.config.yml",
            Path(path) / ".metagit.yml",
            Path(path) / ".metagit.yaml",
        ]

        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config_data = yaml.safe_load(f)
                    return MetagitConfig(**config_data)
                except Exception:
                    continue

        return None

    def run_all(self) -> Union[None, Exception]:
        """
        Run all enabled analysis methods.

        Returns:
            None if successful, Exception if failed
        """
        try:
            # Check if this is a git repository
            try:
                _ = Repo(self.path)
                self.is_git_repo = True
            except (InvalidGitRepositoryError, NoSuchPathError):
                self.is_git_repo = False

            self._extract_metadata()

            language_result = self._detect_languages()
            if isinstance(language_result, Exception):
                self.logger.warning(f"Language detection failed: {language_result}")
            else:
                self.language_detection = language_result

            # Run project type detection
            type_result = self._detect_project_type()
            if isinstance(type_result, Exception):
                self.logger.warning(f"Project type detection failed: {type_result}")
            else:
                self.project_type_detection = type_result

            # Run branch analysis if enabled
            if self.detection_config.branch_analysis_enabled and self.is_git_repo:
                try:
                    self.branch_analysis = GitBranchAnalysis.from_repo(
                        self.path, self.logger
                    )
                    if isinstance(self.branch_analysis, Exception):
                        self.logger.warning(
                            f"Branch analysis failed: {self.branch_analysis}"
                        )
                        self.branch_analysis = None
                except Exception as e:
                    self.logger.warning(f"Branch analysis failed: {e}")

            # Run CI/CD analysis if enabled
            if self.detection_config.ci_config_analysis_enabled:
                try:
                    self.ci_config_analysis = self._ci_config_analysis()
                    if isinstance(self.ci_config_analysis, Exception):
                        self.logger.warning(
                            f"CI/CD analysis failed: {self.ci_config_analysis}"
                        )
                        self.ci_config_analysis = None
                except Exception as e:
                    self.logger.warning(f"CI/CD analysis failed: {e}")

            # Run directory summary analysis if enabled
            if self.detection_config.directory_summary_enabled:
                try:
                    self.directory_summary = directory_summary(self.path)
                except Exception as e:
                    self.logger.warning(f"Directory summary analysis failed: {e}")

            # Run directory details analysis if enabled
            if self.detection_config.directory_details_enabled:
                try:
                    file_lookup = FileExtensionLookup()
                    self.directory_details = directory_details(self.path, file_lookup)
                except Exception as e:
                    self.logger.warning(f"Directory details analysis failed: {e}")

            # Analyze files
            self._analyze_files()

            # Detect metrics
            self._detect_metrics()

            # Update MetagitRecord fields
            self._update_metagit_record()

            self.analysis_completed = True
            self.logger.debug("All analysis methods completed successfully")
            return None

        except Exception as e:
            return e

    def run_specific(self, method_name: str) -> Union[None, Exception]:
        """
        Run a specific analysis method.

        Args:
            method_name: Name of the method to run

        Returns:
            None if successful, Exception if failed
        """
        try:
            self.logger.debug(f"Running specific analysis method: {method_name}")

            if method_name == "language_detection":
                result = self._detect_languages()
                if isinstance(result, Exception):
                    return result
                self.language_detection = result

            elif method_name == "project_type_detection":
                result = self._detect_project_type()
                if isinstance(result, Exception):
                    return result
                self.project_type_detection = result

            elif method_name == "branch_analysis":
                if not self.is_git_repo:
                    return Exception("Branch analysis requires a git repository")
                result = GitBranchAnalysis.from_repo(self.path, self.logger)
                if isinstance(result, Exception):
                    return result
                self.branch_analysis = result

            elif method_name == "ci_config_analysis":
                result = self._ci_config_analysis()
                if isinstance(result, Exception):
                    return result
                self.ci_config_analysis = result

            elif method_name == "directory_summary":
                result = directory_summary(self.path)
                self.directory_summary = result

            elif method_name == "directory_details":
                file_lookup = FileExtensionLookup()
                result = directory_details(self.path, file_lookup)
                self.directory_details = result

            else:
                return Exception(f"Unknown analysis method: {method_name}")

            # Update MetagitRecord fields
            self._update_metagit_record()

            self.logger.debug(f"Successfully ran analysis method: {method_name}")
            return None

        except Exception as e:
            return e

    def _extract_metadata(self) -> None:
        """Extract basic repository metadata."""
        try:
            # Extract name from path if not set
            if not self.name:
                self.name = Path(self.path).name

            # Try to extract description from README files
            readme_files = ["README.md", "README.txt", "README.rst", "README"]
            for readme_file in readme_files:
                readme_path = Path(self.path) / readme_file
                if readme_path.exists():
                    try:
                        with open(readme_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            # Extract first line as description
                            lines = content.split("\n")
                            for line in lines:
                                line = line.strip()
                                if line and not line.startswith("#"):
                                    self.description = line[:200]  # Limit to 200 chars
                                    break
                    except Exception:
                        continue
                    break

        except Exception as e:
            self.logger.warning(f"Metadata extraction failed: {e}")

    def _detect_languages(self) -> Union[LanguageDetection, Exception]:
        """Detect programming languages in the repository."""
        try:
            # This is a simplified language detection
            # In a real implementation, you would use more sophisticated detection
            detected_languages = []
            frameworks = []
            package_managers = []
            build_tools = []

            # Check for common file extensions
            for root, dirs, files in os.walk(self.path):
                for file in files:
                    if file.endswith(".py"):
                        detected_languages.append("Python")
                    elif file.endswith(".js"):
                        detected_languages.append("JavaScript")
                    elif file.endswith(".ts"):
                        detected_languages.append("TypeScript")
                    elif file.endswith(".java"):
                        detected_languages.append("Java")
                    elif file.endswith(".go"):
                        detected_languages.append("Go")
                    elif file.endswith(".rs"):
                        detected_languages.append("Rust")
                    elif file.endswith(".cpp") or file.endswith(".cc"):
                        detected_languages.append("C++")
                    elif file.endswith(".c"):
                        detected_languages.append("C")

                # Check for framework and tool indicators
                if "requirements.txt" in files or "pyproject.toml" in files:
                    package_managers.append("pip")
                if "package.json" in files:
                    package_managers.append("npm")
                if "Cargo.toml" in files:
                    package_managers.append("cargo")
                if "go.mod" in files:
                    package_managers.append("go modules")
                if "pom.xml" in files:
                    package_managers.append("maven")
                if "build.gradle" in files:
                    package_managers.append("gradle")
            package_managers = list(set(package_managers))

            # Determine primary language (most common)
            if detected_languages:
                primary = max(set(detected_languages), key=detected_languages.count)
                secondary = list(set(detected_languages) - {primary})
            else:
                primary = "Unknown"
                secondary = []

            return LanguageDetection(
                primary=primary,
                secondary=secondary,
                frameworks=frameworks,
                package_managers=package_managers,
                build_tools=build_tools,
            )

        except Exception as e:
            return e

    def _detect_project_type(self) -> Union[ProjectTypeDetection, Exception]:
        """Detect project type and domain."""
        try:
            # This is a simplified project type detection
            # In a real implementation, you would use more sophisticated detection
            indicators = []
            project_type = "other"
            domain = "other"
            confidence = 0.5

            # Check for common project indicators
            if any(Path(self.path).glob("*.py")):
                indicators.append("Python files")
                if any(Path(self.path).glob("*.py")):
                    project_type = "application"
                    confidence = 0.7

            if any(Path(self.path).glob("package.json")):
                indicators.append("Node.js project")
                project_type = "application"
                confidence = 0.8

            if any(Path(self.path).glob("Dockerfile")):
                indicators.append("Docker configuration")
                project_type = "application"
                confidence = 0.6

            if any(Path(self.path).glob("*.md")):
                indicators.append("Documentation")
                domain = "documentation"

            return ProjectTypeDetection(
                type=project_type,
                domain=domain,
                confidence=confidence,
                indicators=indicators,
            )

        except Exception as e:
            return e

    def _analyze_files(self) -> None:
        """Analyze files in the repository."""
        try:
            # Check for various file types
            self.has_docker = any(Path(self.path).glob("Dockerfile*"))
            self.has_tests = any(
                Path(self.path).glob("**/test*") or Path(self.path).glob("**/*test*")
            )
            self.has_docs = any(Path(self.path).glob("**/*.md"))
            self.has_iac = any(
                Path(self.path).glob("**/*.tf") or Path(self.path).glob("**/*.yaml")
            )

            # Categorize detected files
            self.detected_files = {
                "docker": [str(f) for f in Path(self.path).glob("Dockerfile*")],
                "tests": [str(f) for f in Path(self.path).glob("**/test*")],
                "docs": [str(f) for f in Path(self.path).glob("**/*.md")],
                "config": [str(f) for f in Path(self.path).glob("**/*.yaml")],
            }

        except Exception as e:
            self.logger.warning(f"File analysis failed: {e}")

    def _detect_metrics(self) -> None:
        """Detect repository metrics."""
        try:
            if not self.is_git_repo:
                return

            repo = Repo(self.path)

            # Create metrics object
            self.metrics = Metrics(
                stars=0,  # Would be fetched from provider API
                forks=0,  # Would be fetched from provider API
                open_issues=0,  # Would be fetched from provider API
                pull_requests=PullRequests(open=0, merged_last_30d=0),
                contributors=len(repo.heads) if repo.heads else 0,
                commit_frequency="unknown",
            )

            # Create metadata object
            self.metadata = RepoMetadata(
                tags=[],
                created_at=None,
                last_commit_at=(
                    repo.head.commit.committed_datetime
                    if repo.head.is_valid()
                    else None
                ),
                default_branch=(
                    repo.active_branch.name if repo.head.is_valid() else None
                ),
                topics=[],
                forked_from=None,
                archived=False,
                template=False,
                has_ci=self.ci_config_analysis is not None,
                has_tests=self.has_tests,
                has_docs=self.has_docs,
                has_docker=self.has_docker,
                has_iac=self.has_iac,
            )

        except Exception as e:
            self.logger.warning(f"Metrics detection failed: {e}")

    def _update_metagit_record(self) -> None:
        """Update MetagitRecord fields with analysis results."""
        try:
            # Update language information
            if self.language_detection:
                self.language = Language(
                    primary=self.language_detection.primary,
                    secondary=self.language_detection.secondary,
                )

            # Update project type information
            if self.project_type_detection:
                self.domain = self.project_type_detection.domain

            # Update branch information
            if self.branch_analysis:
                # Convert BranchInfo to Branch objects
                self.branches = [
                    Branch(
                        name=branch.name,
                        environment=(
                            "production" if branch.name == "main" else "development"
                        ),
                    )
                    for branch in self.branch_analysis.branches
                ]

            # Update detection timestamp
            self.detection_timestamp = datetime.now(timezone.utc)

        except Exception as e:
            self.logger.warning(f"Failed to update MetagitRecord: {e}")

    def summary(self) -> Union[str, Exception]:
        """
        Generate a summary of the repository analysis.

        Returns:
            Summary string or Exception
        """
        try:
            lines = [f"Repository Analysis for: {self.name or self.path}"]
            lines.append(f"Path: {self.path}")
            if self.url:
                lines.append(f"URL: {self.url}")
            lines.append(f"Git repository: {self.is_git_repo}")
            lines.append(f"Cloned: {self.is_cloned}")

            # Language detection
            if self.language_detection:
                lines.append(f"Primary language: {self.language_detection.primary}")
                if self.language_detection.secondary:
                    lines.append(
                        f"Secondary languages: {', '.join(self.language_detection.secondary)}"
                    )
                if self.language_detection.frameworks:
                    lines.append(
                        f"Frameworks: {', '.join(self.language_detection.frameworks)}"
                    )

            # Project type detection
            if self.project_type_detection:
                lines.append(f"Project type: {self.project_type_detection.type}")
                lines.append(f"Domain: {self.project_type_detection.domain}")
                lines.append(f"Confidence: {self.project_type_detection.confidence}")

            # Branch analysis
            if self.branch_analysis:
                lines.append(f"Branch strategy: {self.branch_analysis.strategy_guess}")
                lines.append(
                    f"Number of branches: {len(self.branch_analysis.branches)}"
                )

            # CI/CD analysis
            if self.ci_config_analysis:
                lines.append(f"CI/CD tool: {self.ci_config_analysis.detected_tool}")

            # Directory analysis
            if self.directory_summary:
                lines.append(f"Total files: {self.directory_summary.num_files}")
                lines.append(f"File types: {len(self.directory_summary.file_types)}")

            if self.directory_details:
                lines.append(f"Detailed files: {self.directory_details.num_files}")
                lines.append(
                    f"File categories: {len(self.directory_details.file_types)}"
                )

            # File analysis
            lines.append(f"Has Docker: {self.has_docker}")
            lines.append(f"Has tests: {self.has_tests}")
            lines.append(f"Has docs: {self.has_docs}")
            lines.append(f"Has IaC: {self.has_iac}")

            # Metrics
            if self.metrics:
                lines.append(f"Total commits: {self.metrics.contributors}")
                lines.append(f"Commit frequency: {self.metrics.commit_frequency}")

            return "\n".join(lines)

        except Exception as e:
            return e

    def to_yaml(self) -> Union[str, Exception]:
        """
        Convert DetectionManager to YAML string.

        Returns:
            YAML string or Exception
        """
        try:
            data = self.model_dump(exclude_none=True, exclude_defaults=True)

            # Handle complex objects that can't be serialized directly
            def convert_objects(obj):
                if hasattr(obj, "model_dump"):
                    return obj.model_dump()
                elif isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, Path):
                    return str(obj)
                return obj

            # Convert nested objects
            for key, value in data.items():
                if isinstance(value, dict):
                    data[key] = {k: convert_objects(v) for k, v in value.items()}
                elif isinstance(value, list):
                    data[key] = [convert_objects(v) for v in value]
                else:
                    data[key] = convert_objects(value)

            return yaml.safe_dump(data, indent=2, default_flow_style=False)

        except Exception as e:
            return e

    def to_json(self) -> Union[str, Exception]:
        """
        Convert DetectionManager to JSON string.

        Returns:
            JSON string or Exception
        """
        try:
            data = self.model_dump(exclude_none=True, exclude_defaults=True)

            # Handle complex objects that can't be serialized directly
            def convert_objects(obj):
                if hasattr(obj, "model_dump"):
                    return obj.model_dump()
                elif isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, Path):
                    return str(obj)
                return obj

            # Convert nested objects
            for key, value in data.items():
                if isinstance(value, dict):
                    data[key] = {k: convert_objects(v) for k, v in value.items()}
                elif isinstance(value, list):
                    data[key] = [convert_objects(v) for v in value]
                else:
                    data[key] = convert_objects(value)

            return json.dumps(data, indent=2, default=str)

        except Exception as e:
            return e

    def _ci_config_analysis(
        self, repo_path: str = None
    ) -> Union[CIConfigAnalysis, Exception]:
        """
        Analyze CI/CD configuration in the repository.

        Args:
            repo_path: Path to the repository

        Returns:
            CIConfigAnalysis object or Exception
        """
        if not repo_path:
            repo_path = self.path
        if not Path(repo_path).is_dir():
            return Exception(f"Invalid repository path: {repo_path}")

        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            return Exception(f"Repository path does not exist: {repo_path}")

        try:
            analysis = CIConfigAnalysis()

            # Check for common CI/CD configuration files
            ci_files = self.detection_config.data_ci_file_source

            for file_path, tool_name in ci_files.items():
                full_path = os.path.join(repo_path_obj, file_path)
                if full_path.exists():
                    analysis.detected_tool = tool_name
                    analysis.ci_config_path = str(full_path)

                    # Read configuration content
                    if full_path.is_dir():
                        for file in full_path.iterdir():
                            if file.is_file():
                                with open(file, "r", encoding="utf-8") as f:
                                    analysis.config_content = f.read()
                    else:
                        try:
                            with open(full_path, "r", encoding="utf-8") as f:
                                analysis.config_content = f.read()
                        except Exception as e:
                            self.logger.warning(
                                f"Could not read CI config file {full_path}: {e}"
                            )

                    self.logger.debug(f"Detected CI/CD tool: {tool_name}")
                    break

            # Count pipelines (basic heuristic)
            if analysis.config_content:
                # Simple pipeline counting based on common patterns
                pipeline_indicators = ["job:", "stage:", "pipeline:", "workflow:"]
                analysis.pipeline_count = sum(
                    1
                    for indicator in pipeline_indicators
                    if indicator in analysis.config_content
                )

            return analysis

        except Exception as e:
            self.logger.exception(f"CI/CD analysis failed: {e}")
            return e

    def _branch_analysis(
        self, repo_path: str = "."
    ) -> Union[GitBranchAnalysis, Exception]:
        """
        Analyze the git repository at the given path and return branch information and a strategy guess.
        Uses GitPython for all git operations.

        Args:
            repo_path: Path to the repository

        Returns:
            GitBranchAnalysis object or Exception

        Notes:
          - Should look to replace this with a more sophisticated analysis
          - Should replace GitPython with a more lightweight library
        """

        try:
            repo = Repo(repo_path)
        except (InvalidGitRepositoryError, NoSuchPathError) as e:
            self.logger.exception(f"Invalid git repository at '{repo_path}': {e}")
            return ValueError(f"Invalid git repository at '{repo_path}': {e}")

        # Get local branches
        local_branches = [
            BranchInfo(name=branch.name, is_remote=False)
            for branch in repo.branches
            if branch.name != "HEAD"  # Exclude HEAD branch
        ]

        # Get remote branches
        remote_branches = []
        for remote in repo.remotes:
            for ref in remote.refs:
                # Remove remote name prefix (e.g., 'origin/')
                branch_name = ref.name.split("/", 1)[1] if "/" in ref.name else ref.name
                # Exclude HEAD branch from remote branches
                if branch_name != "HEAD":
                    remote_branches.append(BranchInfo(name=branch_name, is_remote=True))

        # Combine and deduplicate branches (prefer local if name overlaps)
        all_branches_dict = {b.name: b for b in remote_branches}
        all_branches_dict.update({b.name: b for b in local_branches})
        all_branches = list(all_branches_dict.values())

        # Analyze branching strategy
        strategy_guess = self._analyze_branching_strategy(all_branches)

        return GitBranchAnalysis(branches=all_branches, strategy_guess=strategy_guess)

    def _analyze_branching_strategy(self, branches: List[BranchInfo]) -> BranchStrategy:
        """Analyze the branching strategy based on branch names and patterns.

        Args:
            branches: List of BranchInfo objects

        Returns:
            BranchStrategy enum value

        Notes:
          - Should look to replace this with a more sophisticated analysis
          - Should replace GitPython with a more lightweight library
          - Consider custom branch names via appconfig for analysis of additional strategies
        """

        if len(branches) == 0:
            return BranchStrategy.UNKNOWN

        # Only remote branches matter
        remote_branch_names = [b.name for b in branches if b.is_remote]
        # local_branch_names = [b.name for b in branches if not b.is_remote]

        # Check for Git Flow patterns
        if any(name in remote_branch_names for name in ["develop", "master", "main"]):
            if "develop" in remote_branch_names:
                return BranchStrategy.GIT_FLOW

        # Check for GitHub Flow patterns
        if "main" in remote_branch_names or "master" in remote_branch_names:
            if len(remote_branch_names) <= 2:  # main/master + feature branches
                return BranchStrategy.GITHUB_FLOW

        # Check for GitLab Flow patterns
        if any(name in remote_branch_names for name in ["staging", "production"]):
            return BranchStrategy.GITLAB_FLOW

        # Check for Trunk-Based Development
        if len(remote_branch_names) <= 1:
            return BranchStrategy.TRUNK_BASED_DEVELOPMENT

        # Check for Release Branching
        if any(name.startswith("release/") for name in remote_branch_names):
            return BranchStrategy.RELEASE_BRANCHING

        return BranchStrategy.UNKNOWN

    # def cleanup(self) -> None:
    #     """Clean up temporary files if this was a cloned repository."""
    #     if self.is_cloned and self.temp_dir and os.path.exists(self.temp_dir):
    #         try:
    #             shutil.rmtree(self.temp_dir)
    #             self.logger.debug(f"Cleaned up temporary directory: {self.temp_dir}")
    #         except Exception as e:
    #             self.logger.warning(f"Failed to clean up temporary directory: {e}")

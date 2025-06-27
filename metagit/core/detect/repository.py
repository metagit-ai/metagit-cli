#!/usr/bin/env python3

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import yaml
from git import InvalidGitRepositoryError, NoSuchPathError, Repo
from pydantic import BaseModel, Field

from metagit import DATA_PATH
from metagit.core.config.models import (
    AlertingChannel,
    Artifact,
    CommitFrequency,
    Dashboard,
    Environment,
    License,
    LicenseKind,
    Maintainer,
    MetagitConfig,
    Metrics,
    ProjectDomain,
    ProjectKind,
    ProjectType,
    PullRequests,
    RepoMetadata,
    Secret,
    Workspace,
)
from metagit.core.detect.branch import GitBranchAnalysis
from metagit.core.detect.cicd import CIConfigAnalysis
from metagit.core.record.models import MetagitRecord
from metagit.core.utils.common import normalize_git_url
from metagit.core.utils.files import (
    DirectoryDetails,
    DirectorySummary,
    FileExtensionLookup,
    directory_details,
    directory_summary,
)
from metagit.core.utils.logging import LoggingModel, UnifiedLogger


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


class ProjectTypeDetection(BaseModel):
    """Model for project type detection results."""

    type: ProjectType = Field(default=ProjectType.OTHER, description="Project type")
    domain: ProjectDomain = Field(
        default=ProjectDomain.OTHER, description="Project domain"
    )
    confidence: float = Field(default=0.0, description="Detection confidence (0-1)")


class RepositoryAnalysis(LoggingModel):
    """Model for comprehensive repository analysis."""

    path: str = Field(..., description="Repository path")
    url: Optional[str] = Field(None, description="Repository URL")
    kind: ProjectKind = Field(default=ProjectKind.OTHER, description="Project kind")
    is_git_repo: bool = Field(
        default=False, description="Whether this is a git repository"
    )
    is_cloned: bool = Field(
        default=False, description="Whether this was cloned from a URL"
    )
    temp_dir: Optional[str] = Field(None, description="Temporary directory if cloned")

    # Detection results
    language_detection: Optional[LanguageDetection] = None
    project_type_detection: Optional[ProjectTypeDetection] = None

    # Analysis results moved from DetectionManager
    branch_analysis: Optional[GitBranchAnalysis] = None
    ci_config_analysis: Optional[CIConfigAnalysis] = None
    directory_summary: Optional[DirectorySummary] = None
    directory_details: Optional[DirectoryDetails] = None

    # Repository metadata
    name: Optional[str] = None
    description: Optional[str] = None
    license_info: Optional[License] = None
    maintainers: List[Maintainer] = Field(default_factory=list)
    existing_workspace: Optional[Workspace] = None

    # Metrics
    metrics: Optional[Metrics] = None
    metadata: Optional[RepoMetadata] = None
    artifacts: Optional[List[Artifact]] = None
    secrets_management: Optional[List[str]] = None
    secrets: Optional[List[Secret]] = None
    documentation: Optional[List[str]] = None
    alerts: Optional[List[AlertingChannel]] = None
    dashboards: Optional[List[Dashboard]] = None
    environments: Optional[List[Environment]] = None

    # File analysis
    detected_files: Dict[str, List[str]] = Field(default_factory=dict)
    has_docker: bool = Field(default=False)
    has_tests: bool = Field(default=False)
    has_docs: bool = Field(default=False)
    has_iac: bool = Field(default=False)

    model_config = {
        "extra": "allow",
    }

    @classmethod
    def from_path(
        cls, path: str, logger: Optional[UnifiedLogger] = None
    ) -> Union["RepositoryAnalysis", Exception]:
        """
        Analyze a local repository path.

        Args:
            path: Local path to analyze
            logger: Logger instance

        Returns:
            RepositoryAnalysis object or Exception
        """
        logger = logger or UnifiedLogger().get_logger()
        try:
            logger.debug(f"Analyzing local repository at: {path}")

            if not os.path.exists(path):
                return FileNotFoundError(f"Path does not exist: {path}")

            analysis = cls(path=path)
            analysis.set_logger(logger)
            return analysis._run_analysis()
        except Exception as e:
            return e

    @classmethod
    def from_url(
        cls,
        url: str,
        logger: Optional[UnifiedLogger] = None,
        temp_dir: Optional[str] = None,
    ) -> Union["RepositoryAnalysis", Exception]:
        """
        Clone and analyze a repository from URL.

        Args:
            url: Git repository URL
            logger: Logger instance
            temp_dir: Temporary directory for cloning (optional)

        Returns:
            RepositoryAnalysis object or Exception
        """
        logger = logger or UnifiedLogger().get_logger()
        try:
            normalized_url = normalize_git_url(url)
            logger.debug(f"Cloning and analyzing repository from: {normalized_url}")

            # Create temporary directory if not provided
            if temp_dir is None:
                temp_dir = tempfile.mkdtemp(prefix="metagit_")

            # Clone the repository
            try:
                _ = Repo.clone_from(normalized_url, temp_dir)
                logger.debug(f"Successfully cloned repository to: {temp_dir}")
            except Exception as e:
                return Exception(f"Failed to clone repository: {e}")

            analysis = cls(
                path=temp_dir,
                url=normalized_url,
                is_git_repo=True,
                is_cloned=True,
                temp_dir=temp_dir,
            )
            analysis.set_logger(logger)
            return analysis._run_analysis()
        except Exception as e:
            return e

    def _run_analysis(self) -> Union["RepositoryAnalysis", Exception]:
        """
        Run the complete repository analysis.

        Returns:
            Self with analysis results populated
        """
        try:
            self.logger.debug(f"Running analysis for: {self.path}")

            # Check if this is a git repository
            try:
                _ = Repo(self.path)
                self.is_git_repo = True
                self.logger.debug("Repository is a valid git repository")
            except (InvalidGitRepositoryError, NoSuchPathError):
                self.is_git_repo = False
                self.logger.debug("Repository is not a git repository")

            # Extract basic metadata
            self._extract_metadata()

            # Run language detection
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

            # Run branch analysis
            if self.is_git_repo:
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

            # Run CI/CD analysis
            try:
                self.ci_config_analysis = CIConfigAnalysis.from_repo(
                    self.path, self.logger
                )
                if isinstance(self.ci_config_analysis, Exception):
                    self.logger.warning(
                        f"CI/CD analysis failed: {self.ci_config_analysis}"
                    )
                    self.ci_config_analysis = None
            except Exception as e:
                self.logger.warning(f"CI/CD analysis failed: {e}")

            # Run directory summary analysis
            try:
                self.directory_summary = directory_summary(self.path)
            except Exception as e:
                self.logger.warning(f"Directory summary analysis failed: {e}")

            # Run directory details analysis
            try:
                file_lookup = FileExtensionLookup()
                self.directory_details = directory_details(self.path, file_lookup)
            except Exception as e:
                self.logger.warning(f"Directory details analysis failed: {e}")

            # Analyze files
            self._analyze_files()

            # Detect metrics
            self._detect_metrics()

            self.logger.debug("Repository analysis completed successfully")
            return self

        except Exception as e:
            return e

    def _detect_languages(self) -> Union[LanguageDetection, Exception]:
        """
        Detect programming languages used in the repository.

        Returns:
            LanguageDetection object or Exception
        """
        try:
            self.logger.debug("Detecting languages...")

            # Load package manager data
            package_data = self._load_package_manager_data()
            if isinstance(package_data, Exception):
                package_data = {}

            # Load build files data
            build_data = self._load_build_files_data()
            if isinstance(build_data, Exception):
                build_data = {}

            # Initialize detection
            primary_language = "Unknown"
            secondary_languages = []
            frameworks = []
            package_managers = []
            build_tools = []

            # Detect based on package manager files
            for file_name, language in package_data.items():
                if os.path.exists(os.path.join(self.path, file_name)):
                    if primary_language == "Unknown":
                        primary_language = language
                    else:
                        secondary_languages.append(language)

            # Detect based on build files
            for file_name, info in build_data.items():
                if os.path.exists(os.path.join(self.path, file_name)) and isinstance(
                    info, dict
                ):
                    language = info.get("language", "")
                    framework = info.get("framework", "")
                    build_tool = info.get("build_tool", "")
                    package_manager = info.get("package_manager", "")

                    if language and primary_language == "Unknown":
                        primary_language = language
                    elif language and language not in secondary_languages:
                        secondary_languages.append(language)

                    if framework and framework not in frameworks:
                        frameworks.append(framework)

                    if build_tool and build_tool not in build_tools:
                        build_tools.append(build_tool)

                    if package_manager and package_manager not in package_managers:
                        package_managers.append(package_manager)

            # Additional language detection based on file extensions
            if primary_language == "Unknown":
                # Count files by extension to determine primary language
                ext_counts = {}
                for _, dirs, files in os.walk(self.path):
                    # Skip .git directory
                    if ".git" in dirs:
                        dirs.remove(".git")

                    for file in files:
                        _, ext = os.path.splitext(file)
                        ext = ext.lower()
                        ext_counts[ext] = ext_counts.get(ext, 0) + 1

                # Map common extensions to languages
                ext_to_lang = {
                    ".py": "Python",
                    ".js": "JavaScript",
                    ".ts": "TypeScript",
                    ".java": "Java",
                    ".cpp": "C++",
                    ".c": "C",
                    ".go": "Go",
                    ".rs": "Rust",
                    ".php": "PHP",
                    ".rb": "Ruby",
                    ".swift": "Swift",
                    ".kt": "Kotlin",
                    ".scala": "Scala",
                    ".cs": "C#",
                    ".fs": "F#",
                    ".hs": "Haskell",
                    ".ml": "OCaml",
                    ".clj": "Clojure",
                    ".lisp": "Common Lisp",
                    ".r": "R",
                    ".m": "MATLAB",
                    ".pl": "Perl",
                    ".sh": "Shell",
                    ".ps1": "PowerShell",
                    ".bat": "Batch",
                    ".sql": "SQL",
                    ".html": "HTML",
                    ".css": "CSS",
                    ".scss": "SCSS",
                    ".sass": "Sass",
                    ".less": "Less",
                    ".xml": "XML",
                    ".json": "JSON",
                    ".yaml": "YAML",
                    ".yml": "YAML",
                    ".toml": "TOML",
                    ".ini": "INI",
                    ".cfg": "Configuration",
                    ".conf": "Configuration",
                    ".md": "Markdown",
                    ".rst": "reStructuredText",
                    ".tex": "LaTeX",
                    ".dockerfile": "Dockerfile",
                    ".dockerignore": "Docker",
                }

                # Find the most common language
                max_count = 0
                for ext, count in ext_counts.items():
                    if ext in ext_to_lang and count > max_count:
                        primary_language = ext_to_lang[ext]
                        max_count = count

            return LanguageDetection(
                primary=primary_language,
                secondary=secondary_languages,
                frameworks=frameworks,
                package_managers=package_managers,
                build_tools=build_tools,
            )

        except Exception as e:
            return e

    def _detect_project_type(self) -> Union[ProjectTypeDetection, Exception]:
        """
        Detect the type and domain of the project.

        Returns:
            ProjectTypeDetection object or Exception
        """
        try:
            self.logger.debug("Detecting project type...")

            project_type = ProjectType.OTHER
            domain = ProjectDomain.OTHER
            confidence = 0.0

            # Detect based on file patterns and configurations
            has_package_json = os.path.exists(os.path.join(self.path, "package.json"))
            has_pyproject_toml = os.path.exists(
                os.path.join(self.path, "pyproject.toml")
            )
            has_requirements_txt = os.path.exists(
                os.path.join(self.path, "requirements.txt")
            )
            has_cargo_toml = os.path.exists(os.path.join(self.path, "Cargo.toml"))
            has_go_mod = os.path.exists(os.path.join(self.path, "go.mod"))
            has_pom_xml = os.path.exists(os.path.join(self.path, "pom.xml"))
            has_gradle = os.path.exists(os.path.join(self.path, "build.gradle"))
            has_dockerfile = os.path.exists(os.path.join(self.path, "Dockerfile"))
            has_kubernetes = any(
                os.path.exists(os.path.join(self.path, f))
                for f in ["k8s", "kubernetes", "deployment.yaml", "service.yaml"]
            )
            has_terraform = any(
                os.path.exists(os.path.join(self.path, f))
                for f in ["main.tf", "variables.tf", "outputs.tf", ".tf"]
            )
            has_helm = any(
                os.path.exists(os.path.join(self.path, f))
                for f in ["Chart.yaml", "values.yaml"]
            )

            # Determine project type
            if (
                has_package_json
                or has_pyproject_toml
                or has_requirements_txt
                or has_cargo_toml
                or has_go_mod
                or has_pom_xml
                or has_gradle
            ):
                project_type = ProjectType.APPLICATION
                confidence = 0.8
            elif has_terraform:
                project_type = ProjectType.IAC
                confidence = 0.9
            elif has_kubernetes or has_helm:
                project_type = ProjectType.IAC
                confidence = 0.8
            elif has_dockerfile:
                project_type = ProjectType.APPLICATION
                confidence = 0.6

            # Determine domain based on file patterns
            if any(
                os.path.exists(os.path.join(self.path, f))
                for f in ["frontend", "client", "ui", "web", "app.js", "index.html"]
            ):
                domain = ProjectDomain.WEB
            elif any(
                os.path.exists(os.path.join(self.path, f))
                for f in ["android", "ios", "mobile", "react-native"]
            ):
                domain = ProjectDomain.MOBILE
            elif any(
                os.path.exists(os.path.join(self.path, f))
                for f in ["ml", "ai", "model", "tensorflow", "pytorch", "sklearn"]
            ):
                domain = ProjectDomain.ML
            elif any(
                os.path.exists(os.path.join(self.path, f))
                for f in ["docker", "kubernetes", "terraform", "ansible"]
            ):
                domain = ProjectDomain.DEVOPS
            elif any(
                os.path.exists(os.path.join(self.path, f))
                for f in ["database", "db", "sql", "migration"]
            ):
                domain = ProjectDomain.DATABASE

            return ProjectTypeDetection(
                type=project_type,
                domain=domain,
                confidence=confidence,
            )

        except Exception as e:
            return e

    def _analyze_files(self) -> None:
        """Analyze files in the repository for various patterns."""
        try:
            self.logger.debug("Analyzing files...")

            # Check for Docker
            self.has_docker = any(
                os.path.exists(os.path.join(self.path, f))
                for f in ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"]
            )

            # Check for tests
            test_patterns = ["test", "tests", "spec", "specs", "__tests__"]
            self.has_tests = any(
                any(pattern in root.lower() for pattern in test_patterns)
                for root, dirs, files in os.walk(self.path)
            )

            # Check for documentation
            doc_patterns = ["docs", "documentation", "readme", "wiki"]
            self.has_docs = any(
                any(pattern in root.lower() for pattern in doc_patterns)
                for root, dirs, files in os.walk(self.path)
            )

            # Check for Infrastructure as Code
            iac_patterns = [
                "terraform",
                "ansible",
                "puppet",
                "chef",
                "kubernetes",
                "k8s",
            ]
            self.has_iac = any(
                any(pattern in root.lower() for pattern in iac_patterns)
                for root, dirs, files in os.walk(self.path)
            )

        except Exception as e:
            self.logger.warning(f"File analysis failed: {e}")

    def _extract_metadata(self) -> None:
        """Extract basic metadata from the repository."""
        try:
            self.logger.debug("Extracting metadata...")

            # Set name from path
            self.name = os.path.basename(self.path)

            # Try to get description from README
            readme_files = ["README.md", "README.txt", "README.rst", "README"]
            for readme in readme_files:
                readme_path = os.path.join(self.path, readme)
                if os.path.exists(readme_path):
                    try:
                        with open(readme_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            # Extract first paragraph as description
                            lines = content.split("\n")
                            description_lines = []
                            for line in lines:
                                line = line.strip()
                                if line and not line.startswith("#"):
                                    description_lines.append(line)
                                    if len(description_lines) >= 3:  # Limit to 3 lines
                                        break
                            if description_lines:
                                self.description = " ".join(description_lines)
                                break
                    except Exception:
                        continue

            # Try to get license information
            license_files = ["LICENSE", "LICENSE.txt", "LICENSE.md"]
            for license_file in license_files:
                license_path = os.path.join(self.path, license_file)
                if os.path.exists(license_path):
                    try:
                        with open(license_path, "r", encoding="utf-8") as f:
                            content = f.read().lower()
                            if "mit" in content:
                                self.license_info = License(
                                    kind=LicenseKind.MIT, file=license_file
                                )
                            elif "apache" in content:
                                self.license_info = License(
                                    kind=LicenseKind.APACHE_2_0, file=license_file
                                )
                            elif "gpl" in content:
                                self.license_info = License(
                                    kind=LicenseKind.GPL_3_0, file=license_file
                                )
                            else:
                                self.license_info = License(
                                    kind=LicenseKind.CUSTOM, file=license_file
                                )
                            break
                    except Exception:
                        continue

        except Exception as e:
            self.logger.warning(f"Metadata extraction failed: {e}")

    def _load_package_manager_data(self) -> Union[Dict[str, str], Exception]:
        """Load package manager data for language detection."""
        try:
            package_file = os.path.join(DATA_PATH, "package-managers.json")
            with open(package_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            return e

    def _load_build_files_data(self) -> Union[Dict[str, Any], Exception]:
        """Load build files data for language detection."""
        try:
            build_file = os.path.join(DATA_PATH, "build-files.yaml")
            with open(build_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            return e

    def _detect_metrics(self) -> None:
        """Detect repository metrics."""
        try:
            self.logger.debug("Detecting metrics...")

            if not self.is_git_repo:
                return

            repo = Repo(self.path)

            # Basic metrics
            # total_commits = len(list(repo.iter_commits()))
            # total_branches = len(repo.branches)
            # total_tags = len(repo.tags)

            # Get recent activity
            now = datetime.now(timezone.utc)
            recent_commits = 0
            for commit in repo.iter_commits():
                if (now - commit.committed_datetime).days <= 30:
                    recent_commits += 1
                else:
                    break

            # Determine commit frequency
            if recent_commits >= 30:
                commit_frequency = CommitFrequency.DAILY
            elif recent_commits >= 7:
                commit_frequency = CommitFrequency.WEEKLY
            elif recent_commits >= 1:
                commit_frequency = CommitFrequency.MONTHLY
            else:
                commit_frequency = CommitFrequency.MONTHLY

            # Create metrics object
            self.metrics = Metrics(
                stars=0,  # Would need API access for real data
                forks=0,
                open_issues=0,
                pull_requests=PullRequests(open=0, merged_last_30d=0),
                contributors=len(
                    # set(commit.author.email for commit in repo.iter_commits())
                    set(repo.iter_commits())
                ),
                commit_frequency=commit_frequency,
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

    def to_metagit_record(self) -> Union[MetagitRecord, Exception]:
        """
        Convert RepositoryAnalysis to MetagitRecord.

        Returns:
            MetagitRecord object or Exception
        """
        try:
            # Base record data
            record_data = {
                "name": self.name or os.path.basename(self.path),
                "description": self.description,
                "url": self.url,
                "kind": self.kind,
                "detection_timestamp": datetime.now(timezone.utc),
                "detection_source": "remote" if self.is_cloned else "local",
                "detection_version": "1.0.0",
            }

            # Add language information
            if self.language_detection:
                from metagit.core.config.models import Language

                record_data["language"] = Language(
                    primary=self.language_detection.primary,
                    secondary=self.language_detection.secondary,
                )

            # Add project type information
            if self.project_type_detection:
                record_data["domain"] = self.project_type_detection.domain

            # Add branch information
            if self.branch_analysis:
                record_data["branches"] = self.branch_analysis.branches
                record_data["branch_strategy"] = self.branch_analysis.strategy_guess

            # Add metrics
            if self.metrics:
                record_data["metrics"] = self.metrics

            # Add metadata
            if self.metadata:
                record_data["metadata"] = self.metadata

            # Add license information
            if self.license_info:
                record_data["license"] = self.license_info

            # Add maintainers
            if self.maintainers:
                record_data["maintainers"] = self.maintainers

            # Add artifacts
            if self.artifacts:
                record_data["artifacts"] = self.artifacts

            # Add secrets management
            if self.secrets_management:
                record_data["secrets_management"] = self.secrets_management

            # Add secrets
            if self.secrets:
                record_data["secrets"] = self.secrets

            # Add documentation
            if self.documentation:
                record_data["documentation"] = self.documentation

            # Add observability information
            observability_data = {}
            if self.alerts:
                observability_data["alerting_channels"] = self.alerts
            if self.dashboards:
                observability_data["dashboards"] = self.dashboards

            if observability_data:
                from metagit.core.config.models import Observability

                record_data["observability"] = Observability(**observability_data)

            # Add deployment information
            deployment_data = {}
            if self.environments:
                deployment_data["environments"] = self.environments

            if deployment_data:
                from metagit.core.config.models import Deployment

                record_data["deployment"] = Deployment(**deployment_data)

            return MetagitRecord(**record_data)

        except Exception as e:
            return e

    def to_metagit_config(self) -> Union[MetagitConfig, Exception]:
        """
        Convert RepositoryAnalysis to MetagitConfig.

        Returns:
            MetagitConfig object or Exception
        """
        try:
            # Base config data
            config_data = {
                "name": self.name or os.path.basename(self.path),
                "description": self.description,
                "url": self.url,
                "kind": self.kind,
            }

            # Add language information
            if self.language_detection:
                from metagit.core.config.models import Language

                config_data["language"] = Language(
                    primary=self.language_detection.primary,
                    secondary=self.language_detection.secondary,
                )

            # Add project type information
            if self.project_type_detection:
                config_data["domain"] = self.project_type_detection.domain

            # Add branch information
            if self.branch_analysis:
                config_data["branches"] = self.branch_analysis.branches
                config_data["branch_strategy"] = self.branch_analysis.strategy_guess

            # Add license information
            if self.license_info:
                config_data["license"] = self.license_info

            # Add maintainers
            if self.maintainers:
                config_data["maintainers"] = self.maintainers

            # Add artifacts
            if self.artifacts:
                config_data["artifacts"] = self.artifacts

            # Add secrets management
            if self.secrets_management:
                config_data["secrets_management"] = self.secrets_management

            # Add secrets
            if self.secrets:
                config_data["secrets"] = self.secrets

            # Add documentation
            if self.documentation:
                config_data["documentation"] = self.documentation

            # Add CI/CD information
            if self.ci_config_analysis:
                from metagit.core.config.models import CICD, Pipeline

                pipelines = []
                for tool in self.ci_config_analysis.detected_tools:
                    pipelines.append(Pipeline(name=tool, ref=f".{tool}"))

                config_data["cicd"] = CICD(
                    platform=self.ci_config_analysis.detected_tool,
                    pipelines=pipelines,
                )

            # Add observability information
            observability_data = {}
            if self.alerts:
                observability_data["alerting_channels"] = self.alerts
            if self.dashboards:
                observability_data["dashboards"] = self.dashboards

            if observability_data:
                from metagit.core.config.models import Observability

                config_data["observability"] = Observability(**observability_data)

            # Add deployment information
            deployment_data = {}
            if self.environments:
                deployment_data["environments"] = self.environments

            if deployment_data:
                from metagit.core.config.models import Deployment

                config_data["deployment"] = Deployment(**deployment_data)

            return MetagitConfig(**config_data)

        except Exception as e:
            return e

    def cleanup(self) -> None:
        """Clean up temporary files if this was a cloned repository."""
        if self.is_cloned and self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                self.logger.debug(f"Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up temporary directory: {e}")

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

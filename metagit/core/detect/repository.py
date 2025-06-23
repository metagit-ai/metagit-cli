#!/usr/bin/env python3

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

import yaml
from dotenv import load_dotenv
from git import InvalidGitRepositoryError, NoSuchPathError, Repo
from pydantic import BaseModel, Field

from metagit.core.config.models import (
    CICD,
    Branch,
    BranchStrategy,
    CICDPlatform,
    CommitFrequency,
    License,
    LicenseKind,
    Maintainer,
    MetagitConfig,
    Metrics,
    Pipeline,
    ProjectDomain,
    ProjectKind,
    ProjectPath,
    ProjectType,
    PullRequests,
    RepoMetadata,
    Tasker,
    TaskerKind,
    Workspace,
    WorkspaceProject,
)
from metagit.core.detect.branch import GitBranchAnalysis
from metagit.core.detect.cicd import CIConfigAnalysis
from metagit.core.providers import registry

load_dotenv()

default_logger = logging.getLogger("RepositoryAnalysis")
default_logger.setLevel(logging.INFO)
if not default_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    default_logger.addHandler(handler)


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


class RepositoryAnalysis(BaseModel):
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
    branch_analysis: Optional[GitBranchAnalysis] = None
    ci_config_analysis: Optional[CIConfigAnalysis] = None

    # Repository metadata
    name: Optional[str] = None
    description: Optional[str] = None
    license_info: Optional[License] = None
    maintainers: List[Maintainer] = Field(default_factory=list)
    existing_workspace: Optional[Workspace] = None

    # Metrics
    metrics: Optional[Metrics] = None

    # File analysis
    detected_files: Dict[str, List[str]] = Field(default_factory=dict)
    has_docker: bool = Field(default=False)
    has_tests: bool = Field(default=False)
    has_docs: bool = Field(default=False)
    has_iac: bool = Field(default=False)

    logger: Optional[Any] = None
    model_config = {
        "extra": "allow",
        "exclude": {"logger", "existing_workspace"},
    }

    def model_post_init(self, __context: Any) -> None:
        """Initialize logger after model creation."""
        self.logger = self.logger or default_logger

    @classmethod
    def from_path(
        cls, path: str, logger: Optional[Any] = None
    ) -> Union["RepositoryAnalysis", Exception]:
        """
        Analyze a local repository path.

        Args:
            path: Local path to analyze
            logger: Logger instance

        Returns:
            RepositoryAnalysis object or Exception
        """
        try:
            logger = logger or default_logger
            logger.debug(f"Analyzing local repository at: {path}")

            if not os.path.exists(path):
                return FileNotFoundError(f"Path does not exist: {path}")

            analysis = cls(path=path, logger=logger)
            return analysis._run_analysis()
        except Exception as e:
            return e

    @classmethod
    def from_url(
        cls, url: str, logger: Optional[Any] = None, temp_dir: Optional[str] = None
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
        try:
            logger = logger or default_logger
            logger.debug(f"Cloning and analyzing repository from: {url}")

            # Create temporary directory if not provided
            if temp_dir is None:
                temp_dir = tempfile.mkdtemp(prefix="metagit_")

            # Clone the repository
            try:
                _ = Repo.clone_from(url, temp_dir)
                logger.debug(f"Successfully cloned repository to: {temp_dir}")
            except Exception as e:
                return Exception(f"Failed to clone repository: {e}")

            analysis = cls(
                path=temp_dir,
                url=url,
                is_git_repo=True,
                is_cloned=True,
                temp_dir=temp_dir,
                logger=logger,
            )
            return analysis._run_analysis()
        except Exception as e:
            return e

    def _load_existing_workspace(self) -> None:
        """Check for and load an existing .metagit.yml file's workspace."""
        config_path = os.path.join(self.path, ".metagit.yml")
        if os.path.exists(config_path):
            self.logger.debug(f"Found existing .metagit.yml at: {config_path}")
            try:
                with open(config_path, "r") as f:
                    data = yaml.safe_load(f)
                if data and "workspace" in data:
                    self.existing_workspace = Workspace(**data["workspace"])
                    self.logger.debug("Loaded existing workspace configuration.")
            except Exception as e:
                self.logger.warning(
                    f"Failed to load or parse existing .metagit.yml: {e}"
                )

    def _run_analysis(self) -> Union["RepositoryAnalysis", Exception]:
        """Run the complete analysis pipeline."""
        try:
            # Check for existing .metagit.yml and load workspace
            self._load_existing_workspace()

            # Check if it's a git repository
            try:
                _ = Repo(self.path)
                self.is_git_repo = True
                self.logger.debug("Repository is a valid git repository")
            except (InvalidGitRepositoryError, NoSuchPathError):
                self.is_git_repo = False
                self.logger.debug("Path is not a git repository")

            # Analyze files and structure first
            self._analyze_files()

            # Detect languages and technologies
            self.language_detection = self._detect_languages()
            if isinstance(self.language_detection, Exception):
                return self.language_detection

            # Detect project type (now that files are analyzed)
            self.project_type_detection = self._detect_project_type()
            if isinstance(self.project_type_detection, Exception):
                return self.project_type_detection

            # Extract repository metadata
            self._extract_metadata()

            # Run git-specific analysis if applicable
            if self.is_git_repo:
                self.branch_analysis = GitBranchAnalysis.from_repo(
                    self.path, self.logger
                )
                if isinstance(self.branch_analysis, Exception):
                    self.logger.warning(
                        f"Branch analysis failed: {self.branch_analysis}"
                    )
                    self.branch_analysis = None

                self.ci_config_analysis = CIConfigAnalysis.from_repo(
                    self.path, self.logger
                )
                if isinstance(self.ci_config_analysis, Exception):
                    self.logger.warning(
                        f"CI/CD analysis failed: {self.ci_config_analysis}"
                    )
                    self.ci_config_analysis = None

            # Detect repository metrics
            self._detect_metrics()

            return self
        except Exception as e:
            return e

    def _detect_languages(self) -> Union[LanguageDetection, Exception]:
        """Detect programming languages and technologies."""
        try:
            # Load package manager data
            package_manager_data = self._load_package_manager_data()
            if isinstance(package_manager_data, Exception):
                return package_manager_data

            # Load build files data
            build_files_data = self._load_build_files_data()
            if isinstance(build_files_data, Exception):
                return build_files_data

            detected_languages = set()
            detected_package_managers = set()
            detected_build_tools = set()
            detected_frameworks = set()

            # Scan for package manager files
            for root, dirs, files in os.walk(self.path):
                # Skip hidden directories and common exclusions
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d not in ["node_modules", "venv", "__pycache__"]
                ]

                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, self.path)

                    # Check package managers
                    if file in package_manager_data:
                        language = package_manager_data[file]
                        detected_languages.add(language)
                        detected_package_managers.add(file)

                    # Check build tools
                    if file in build_files_data.get("build_files", {}).get(
                        "general", []
                    ):
                        detected_build_tools.add(file)

                    # Language-specific detection
                    if file.endswith(".py"):
                        detected_languages.add("Python")
                    elif file.endswith(".js") or file.endswith(".ts"):
                        detected_languages.add("JavaScript")
                        if "react" in file.lower() or "react" in relative_path.lower():
                            detected_frameworks.add("React")
                        if "vue" in file.lower() or "vue" in relative_path.lower():
                            detected_frameworks.add("Vue")
                        if (
                            "angular" in file.lower()
                            or "angular" in relative_path.lower()
                        ):
                            detected_frameworks.add("Angular")
                    elif file.endswith(".go"):
                        detected_languages.add("Go")
                    elif file.endswith(".rs"):
                        detected_languages.add("Rust")
                    elif file.endswith(".java"):
                        detected_languages.add("Java")
                    elif file.endswith(".cs"):
                        detected_languages.add("C#")
                    elif file.endswith(".php"):
                        detected_languages.add("PHP")
                    elif file.endswith(".rb"):
                        detected_languages.add("Ruby")
                    elif file.endswith(".ex"):
                        detected_languages.add("Elixir")
                    elif file.endswith(".hs"):
                        detected_languages.add("Haskell")
                    elif file.endswith(".scala"):
                        detected_languages.add("Scala")
                    elif file.endswith(".clj"):
                        detected_languages.add("Clojure")
                    elif file.endswith(".kt"):
                        detected_languages.add("Kotlin")
                    elif file.endswith(".swift"):
                        detected_languages.add("Swift")
                    elif file.endswith(".m"):
                        detected_languages.add("Objective-C")
                    elif (
                        file.endswith(".cpp")
                        or file.endswith(".cc")
                        or file.endswith(".cxx")
                    ):
                        detected_languages.add("C++")
                    elif file.endswith(".c"):
                        detected_languages.add("C")
                    elif file.endswith(".h"):
                        detected_languages.add("C/C++")
                    elif file.endswith(".sh") or file.endswith(".bash"):
                        detected_languages.add("Shell")
                    elif file.endswith(".tf"):
                        detected_languages.add("Terraform")
                        detected_frameworks.add("Terraform")
                    elif file.endswith(".yaml") or file.endswith(".yml"):
                        if "kubernetes" in file.lower() or "k8s" in file.lower():
                            detected_frameworks.add("Kubernetes")

            # Determine primary language (most files or most specific)
            primary_language = "Unknown"
            if detected_languages:
                # Simple heuristic: prefer more specific languages
                language_priority = {
                    "Python": 10,
                    "JavaScript": 9,
                    "Go": 8,
                    "Rust": 7,
                    "Java": 6,
                    "C#": 5,
                    "PHP": 4,
                    "Ruby": 3,
                    "C++": 2,
                    "C": 1,
                }
                primary_language = max(
                    detected_languages, key=lambda x: language_priority.get(x, 0)
                )

            return LanguageDetection(
                primary=primary_language,
                secondary=list(detected_languages - {primary_language}),
                frameworks=list(detected_frameworks),
                package_managers=list(detected_package_managers),
                build_tools=list(detected_build_tools),
            )
        except Exception as e:
            return e

    def _detect_project_type(self) -> Union[ProjectTypeDetection, Exception]:
        """Detect project type and domain."""
        try:
            project_type = ProjectType.OTHER
            domain = ProjectDomain.OTHER
            confidence = 0.0

            # Collect all detected files for analysis
            all_files = []
            for category_files in self.detected_files.values():
                all_files.extend(category_files)

            # Check for specific project indicators
            if self.language_detection:
                # CLI tools
                if any("cli" in f.lower() for f in all_files):
                    project_type = ProjectType.CLI
                    confidence = 0.8

                # Infrastructure as Code
                elif any(f.endswith(".tf") for f in all_files):
                    project_type = ProjectType.IAC
                    domain = ProjectDomain.DEVOPS
                    confidence = 0.9

                # Web applications
                elif any(
                    f.endswith((".html", ".js", ".ts", ".jsx", ".tsx"))
                    for f in all_files
                ):
                    project_type = ProjectType.APPLICATION
                    domain = ProjectDomain.WEB
                    confidence = 0.7

                # Libraries
                elif self.language_detection.primary in [
                    "Python",
                    "JavaScript",
                    "Go",
                    "Rust",
                ]:
                    # Check for library indicators
                    if any(
                        f
                        in ["setup.py", "pyproject.toml", "package.json", "Cargo.toml"]
                        for f in all_files
                    ):
                        project_type = ProjectType.LIBRARY
                        confidence = 0.6

                # Microservices
                elif any("docker" in f.lower() for f in all_files):
                    project_type = ProjectType.MICROSERVICE
                    confidence = 0.7

                # Data science
                elif any(f.endswith((".ipynb", ".py")) for f in all_files):
                    if any(
                        "data" in f.lower() or "ml" in f.lower() or "ai" in f.lower()
                        for f in all_files
                    ):
                        project_type = ProjectType.DATA_SCIENCE
                        domain = ProjectDomain.ML
                        confidence = 0.8

            return ProjectTypeDetection(
                type=project_type, domain=domain, confidence=confidence
            )
        except Exception as e:
            return e

    def _analyze_files(self) -> None:
        """Analyze repository files and structure."""
        try:
            files_by_category = {
                "docker": [],
                "testing": [],
                "documentation": [],
                "iac": [],
                "ci_cd": [],
                "build": [],
                "config": [],
            }

            for root, dirs, files in os.walk(self.path):
                # Skip hidden directories and common exclusions
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d not in ["node_modules", "venv", "__pycache__"]
                ]

                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, self.path)

                    # Docker files
                    if file.lower() in [
                        "dockerfile",
                        "docker-compose.yml",
                        "docker-compose.yaml",
                    ]:
                        files_by_category["docker"].append(relative_path)
                        self.has_docker = True

                    # Testing files
                    elif any(
                        test in file.lower()
                        for test in ["test", "spec", "jest", "pytest", "unittest"]
                    ):
                        files_by_category["testing"].append(relative_path)
                        self.has_tests = True

                    # Documentation files
                    elif any(
                        doc in file.lower()
                        for doc in ["readme", "docs", "documentation", ".md"]
                    ):
                        files_by_category["documentation"].append(relative_path)
                        self.has_docs = True

                    # Infrastructure as Code
                    elif file.endswith((".tf", ".yaml", ".yml")) and any(
                        iac in file.lower()
                        for iac in ["terraform", "kubernetes", "helm", "ansible"]
                    ):
                        files_by_category["iac"].append(relative_path)
                        self.has_iac = True

                    # CI/CD files
                    elif any(
                        ci in file.lower()
                        for ci in [".github", ".gitlab", "jenkins", "travis", "circle"]
                    ):
                        files_by_category["ci_cd"].append(relative_path)

                    # Build files
                    elif any(
                        build in file.lower()
                        for build in ["makefile", "build", "gradle", "maven", "ant"]
                    ):
                        files_by_category["build"].append(relative_path)

                    # Config files
                    elif any(
                        config in file.lower()
                        for config in [
                            ".config",
                            ".conf",
                            ".ini",
                            ".json",
                            ".yaml",
                            ".yml",
                        ]
                    ):
                        files_by_category["config"].append(relative_path)

            self.detected_files = files_by_category

        except Exception as e:
            self.logger.warning(f"File analysis failed: {e}")

    def _extract_metadata(self) -> None:
        """Extract repository metadata."""
        try:
            # Extract name from path
            self.name = os.path.basename(os.path.abspath(self.path))

            # Try to get description from README
            readme_files = ["README.md", "README.txt", "README.rst", "readme.md"]
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
                                    if len(" ".join(description_lines)) > 200:
                                        break
                            if description_lines:
                                self.description = " ".join(description_lines)[:200]
                                break
                    except Exception:
                        continue

            # Try to detect license
            license_files = [
                "LICENSE",
                "LICENSE.txt",
                "LICENSE.md",
                "license",
                "COPYING",
            ]
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
                            elif "bsd" in content:
                                self.license_info = License(
                                    kind=LicenseKind.BSD_3_CLAUSE, file=license_file
                                )
                            else:
                                self.license_info = License(
                                    kind=LicenseKind.NONE, file=license_file
                                )
                            break
                    except Exception:
                        continue

            # Extract maintainers from git if available
            if self.is_git_repo:
                try:
                    repo = Repo(self.path)
                    # Get recent contributors
                    commits = list(repo.iter_commits("HEAD", max_count=100))
                    contributors = {}
                    for commit in commits:
                        author = commit.author
                        if author.email not in contributors:
                            contributors[author.email] = {
                                "name": author.name,
                                "email": author.email,
                                "commits": 0,
                            }
                        contributors[author.email]["commits"] += 1

                    # Convert to maintainers (top 5 contributors)
                    sorted_contributors = sorted(
                        contributors.values(), key=lambda x: x["commits"], reverse=True
                    )
                    for contributor in sorted_contributors[:5]:
                        self.maintainers.append(
                            Maintainer(
                                name=contributor["name"],
                                email=contributor["email"],
                                role="Contributor",
                            )
                        )
                except Exception as e:
                    self.logger.debug(f"Failed to extract maintainers: {e}")

        except Exception as e:
            self.logger.warning(f"Metadata extraction failed: {e}")

    def _load_package_manager_data(self) -> Union[Dict[str, str], Exception]:
        """Load package manager detection data."""
        try:
            data_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "package-managers.json"
            )
            with open(data_path, "r") as f:
                return json.load(f)
        except Exception as e:
            return e

    def _load_build_files_data(self) -> Union[Dict[str, Any], Exception]:
        """Load build files detection data."""
        try:
            data_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "data", "build-files.yaml"
            )
            with open(data_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            return e

    def _detect_metrics(self) -> None:
        """Detect repository metrics from git history and available data."""
        try:
            if not self.is_git_repo:
                self.logger.debug("Not a git repository, skipping metrics detection")
                return

            repo = Repo(self.path)

            # Try to get remote URL to determine if we can fetch metrics from a provider
            remote_url = None
            if repo.remotes:
                origin = next((r for r in repo.remotes if r.name == "origin"), None)
                if origin and origin.urls:
                    remote_url = next(iter(origin.urls), None)

            # Try to use provider plugins for real metrics
            if remote_url:
                provider = registry.get_provider_for_url(remote_url)
                if provider:
                    self.logger.debug(
                        f"Using {provider.get_name()} provider for metrics"
                    )
                    try:
                        repo_info = provider.extract_repo_info(remote_url)
                        owner = repo_info["owner"]
                        repo_name = repo_info["repo"]

                        # Get metrics from provider
                        provider_metrics = provider.get_repository_metrics(
                            owner, repo_name
                        )
                        if isinstance(provider_metrics, Metrics):
                            self.metrics = provider_metrics
                            self.logger.debug(
                                f"Successfully fetched metrics from {provider.get_name()}"
                            )
                            return
                        else:
                            self.logger.warning(
                                f"Provider metrics failed: {provider_metrics}"
                            )
                    except Exception as e:
                        self.logger.warning(f"Provider metrics failed: {e}")

            # Fallback to git-based metrics
            self.logger.debug("Using git-based metrics detection")

            # Get all commits
            commits = list(repo.iter_commits("HEAD"))
            if not commits:
                self.logger.debug("No commits found, skipping metrics detection")
                return

            # Count contributors (unique authors)
            contributors = set()
            for commit in commits:
                if commit.author.email:
                    contributors.add(commit.author.email)

            # Calculate commit frequency
            if len(commits) > 1:
                first_commit_date = commits[-1].committed_datetime
                last_commit_date = commits[0].committed_datetime
                days_between = (last_commit_date - first_commit_date).days

                if days_between > 0:
                    commits_per_day = len(commits) / days_between
                    if commits_per_day >= 1:
                        commit_frequency = CommitFrequency.DAILY
                    elif commits_per_day >= 1 / 7:  # At least 1 commit per week
                        commit_frequency = CommitFrequency.WEEKLY
                    else:
                        commit_frequency = CommitFrequency.MONTHLY
                else:
                    commit_frequency = CommitFrequency.DAILY
            else:
                commit_frequency = CommitFrequency.MONTHLY

            # Count pull requests (approximation based on merge commits)
            merge_commits = [c for c in commits if len(c.parents) > 1]
            merged_last_30d = 0
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

            for commit in merge_commits:
                if commit.committed_datetime >= thirty_days_ago:
                    merged_last_30d += 1

            # For now, we'll use default values for stars, forks, and issues
            # These would typically come from API calls to GitHub/GitLab/etc.
            stars = 0
            forks = 0
            open_issues = 0
            open_prs = 0

            # Create pull requests object
            pull_requests = PullRequests(open=open_prs, merged_last_30d=merged_last_30d)

            # Create metrics object
            self.metrics = Metrics(
                stars=stars,
                forks=forks,
                open_issues=open_issues,
                pull_requests=pull_requests,
                contributors=len(contributors),
                commit_frequency=commit_frequency,
            )

            self.logger.debug(
                f"Detected metrics: {len(contributors)} contributors, {commit_frequency.value} commit frequency"
            )

        except Exception as e:
            self.logger.warning(f"Metrics detection failed: {e}")
            # Set default metrics if detection fails
            self.metrics = Metrics(
                stars=0,
                forks=0,
                open_issues=0,
                pull_requests=PullRequests(open=0, merged_last_30d=0),
                contributors=0,
                commit_frequency=CommitFrequency.MONTHLY,
            )

    def to_metagit_config(self) -> Union[MetagitConfig, Exception]:
        """Convert analysis results to MetagitConfig object."""
        try:
            # Determine branch strategy
            branch_strategy = BranchStrategy.NONE
            if self.branch_analysis and self.branch_analysis.strategy_guess:
                strategy_map = {
                    "Git Flow": BranchStrategy.GITFLOW,
                    "GitHub Flow": BranchStrategy.GITHUBFLOW,
                    "GitLab Flow": BranchStrategy.GITLABFLOW,
                    "Trunk-Based Development": BranchStrategy.TRUNK,
                    "Release Branching": BranchStrategy.CUSTOM,
                }
                branch_strategy = strategy_map.get(
                    self.branch_analysis.strategy_guess, BranchStrategy.NONE
                )

            # Create CI/CD configuration
            cicd_config = None
            if self.ci_config_analysis and self.ci_config_analysis.detected_tool:
                platform_map = {
                    "GitHub Actions": CICDPlatform.GITHUB,
                    "GitLab CI": CICDPlatform.GITLAB,
                    "CircleCI": CICDPlatform.CIRCLECI,
                    "Jenkins": CICDPlatform.JENKINS,
                }
                platform = platform_map.get(
                    self.ci_config_analysis.detected_tool, CICDPlatform.CUSTOM
                )
                cicd_config = CICD(
                    platform=platform,
                    pipelines=[
                        Pipeline(
                            name="default",
                            ref=self.ci_config_analysis.ci_config_path or "unknown",
                        )
                    ],
                )

            # Create taskers
            taskers = []
            # Collect all detected files for analysis
            all_files = []
            for category_files in self.detected_files.values():
                all_files.extend(category_files)

            if any("taskfile" in f.lower() for f in all_files):
                taskers.append(Tasker(kind=TaskerKind.TASKFILE))
            if any("makefile" in f.lower() for f in all_files):
                taskers.append(Tasker(kind=TaskerKind.MAKEFILE))

            # Create branches
            branches = []
            if self.branch_analysis:
                for branch_info in self.branch_analysis.branches:
                    branches.append(Branch(name=branch_info.name))

            # Create workspace if none exists
            workspace = self.existing_workspace
            if not workspace:
                workspace = Workspace(
                    projects=[
                        WorkspaceProject(
                            name="default",
                            repos=[
                                ProjectPath(
                                    name=self.name or "unknown",
                                    path=self.path,
                                    url=self.url,
                                )
                            ],
                        )
                    ]
                )

            # Create repository metadata
            metadata = RepoMetadata(
                default_branch=(
                    self.branch_analysis.branches[0].name
                    if self.branch_analysis and self.branch_analysis.branches
                    else None
                ),
                has_ci=self.ci_config_analysis is not None,
                has_tests=self.has_tests,
                has_docs=self.has_docs,
                has_docker=self.has_docker,
                has_iac=self.has_iac,
                created_at=datetime.now(
                    timezone.utc
                ),  # Would need git history for actual creation date
                last_commit_at=datetime.now(
                    timezone.utc
                ),  # Would need git history for actual last commit
            )

            return MetagitConfig(
                name=self.name or "Unknown Project",
                description=self.description,
                url=self.url,
                kind=(
                    self.project_type_detection.type
                    if self.project_type_detection
                    else ProjectKind.OTHER
                ),
                license=self.license_info,
                maintainers=self.maintainers,
                branch_strategy=branch_strategy,
                taskers=taskers,
                branches=branches,
                cicd=cicd_config,
                metrics=self.metrics,
                metadata=metadata,
                workspace=workspace,
            )
        except Exception as e:
            return e

    def cleanup(self) -> None:
        """Clean up temporary resources."""
        if self.is_cloned and self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil

                shutil.rmtree(self.temp_dir)
                self.logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                self.logger.warning(f"Failed to cleanup temporary directory: {e}")

    def summary(self) -> Union[str, Exception]:
        """Generate a summary of the analysis."""
        try:
            lines = ["Repository Analysis Summary"]
            lines.append(f"Path: {self.path}")
            if self.url:
                lines.append(f"URL: {self.url}")
            lines.append(f"Git Repository: {self.is_git_repo}")

            # Check if provider was used for metrics
            provider_used = None
            if self.is_git_repo:
                try:
                    from git import Repo

                    repo = Repo(self.path)
                    if repo.remotes:
                        origin = next(
                            (r for r in repo.remotes if r.name == "origin"), None
                        )
                        if origin and origin.urls:
                            remote_url = next(iter(origin.urls), None)
                            if remote_url:
                                provider = registry.get_provider_for_url(remote_url)
                                if provider:
                                    provider_used = provider.get_name()
                except Exception:
                    pass

            if self.language_detection:
                lines.append(f"Primary Language: {self.language_detection.primary}")
                if self.language_detection.secondary:
                    lines.append(
                        f"Secondary Languages: {', '.join(self.language_detection.secondary)}"
                    )
                if self.language_detection.frameworks:
                    lines.append(
                        f"Frameworks: {', '.join(self.language_detection.frameworks)}"
                    )
                if self.language_detection.package_managers:
                    lines.append(
                        f"Package Managers: {', '.join(self.language_detection.package_managers)}"
                    )

            if self.project_type_detection:
                # Safely get enum values
                project_type = self.project_type_detection.type
                project_type_str = (
                    project_type.value
                    if hasattr(project_type, "value")
                    else str(project_type)
                )

                domain = self.project_type_detection.domain
                domain_str = domain.value if hasattr(domain, "value") else str(domain)

                lines.append(f"Project Type: {project_type_str}")
                lines.append(f"Domain: {domain_str}")
                lines.append(
                    f"Confidence: {self.project_type_detection.confidence:.2f}"
                )

            if self.branch_analysis:
                lines.append(f"Branch Strategy: {self.branch_analysis.strategy_guess}")
                lines.append(
                    f"Number of Branches: {len(self.branch_analysis.branches)}"
                )

            if self.ci_config_analysis:
                lines.append(f"CI/CD Tool: {self.ci_config_analysis.detected_tool}")

            if self.metrics:
                lines.append(f"Contributors: {self.metrics.contributors}")

                # Safely get commit frequency value
                commit_frequency = self.metrics.commit_frequency
                commit_frequency_str = (
                    commit_frequency.value
                    if hasattr(commit_frequency, "value")
                    else str(commit_frequency)
                )
                lines.append(f"Commit Frequency: {commit_frequency_str}")

                lines.append(f"Stars: {self.metrics.stars}")
                lines.append(f"Forks: {self.metrics.forks}")
                lines.append(f"Open Issues: {self.metrics.open_issues}")
                lines.append(f"Open PRs: {self.metrics.pull_requests.open}")
                lines.append(
                    f"PRs Merged (30d): {self.metrics.pull_requests.merged_last_30d}"
                )

                # Add provider information
                if provider_used:
                    lines.append(f"Metrics Source: {provider_used} API")
                else:
                    lines.append("Metrics Source: Git-based estimation")

            lines.append(f"Has Docker: {self.has_docker}")
            lines.append(f"Has Tests: {self.has_tests}")
            lines.append(f"Has Documentation: {self.has_docs}")
            lines.append(f"Has Infrastructure as Code: {self.has_iac}")

            return "\n".join(lines)
        except Exception as e:
            return e

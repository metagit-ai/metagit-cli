#!/usr/bin/env python
"""
Pydantic models for .metagit.yml configuration file.

This module defines the data models used to parse and validate
the .metagit.yml configuration file structure.
"""

import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional, Union

import yaml
from pydantic import BaseModel, Field, HttpUrl, field_serializer, field_validator

from metagit.core.appconfig.models import AppConfig
from metagit.core.project.models import GitUrl, ProjectKind, ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


class LicenseKind(str, Enum):
    """Enumeration of license kinds."""

    NONE = "None"
    MIT = "MIT"
    APACHE_2_0 = "Apache-2.0"
    GPL_3_0 = "GPL-3.0"
    BSD_3_CLAUSE = "BSD-3-Clause"
    PROPRIETARY = "proprietary"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class BranchStrategy(str, Enum):
    """Enumeration of branch strategies."""

    TRUNK = "trunk"
    GITFLOW = "gitflow"
    GITHUBFLOW = "githubflow"
    GITLABFLOW = "gitlabflow"
    FORK = "fork"
    NONE = "none"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class TaskerKind(str, Enum):
    """Enumeration of tasker kinds."""

    TASKFILE = "Taskfile"
    MAKEFILE = "Makefile"
    JEST = "Jest"
    NPM = "NPM"
    ATMOS = "Atmos"
    CUSTOM = "custom"
    NONE = "none"
    MISE_TASKS = "mise_tasks"


class ArtifactType(str, Enum):
    """Enumeration of artifact types."""

    DOCKER = "docker"
    GITHUB_RELEASE = "github_release"
    HELM_CHART = "helm_chart"
    NPM_PACKAGE = "npm_package"
    STATIC_WEBSITE = "static_website"
    PYTHON_PACKAGE = "python_package"
    NODE_PACKAGE = "node_package"
    RUBY_PACKAGE = "ruby_package"
    JAVA_PACKAGE = "java_package"
    C_PACKAGE = "c_package"
    CPP_PACKAGE = "cpp_package"
    CSHARP_PACKAGE = "csharp_package"
    GO_PACKAGE = "go_package"
    RUST_PACKAGE = "rust_package"
    PHP_PACKAGE = "php_package"
    DOTNET_PACKAGE = "dotnet_package"
    ELIXIR_PACKAGE = "elixir_package"
    HASKELL_PACKAGE = "haskell_package"
    CUSTOM = "custom"
    NONE = "none"
    UNKNOWN = "unknown"
    OTHER = "other"
    PLUGIN = "plugin"
    TEMPLATE = "template"
    CONFIG = "config"
    BINARY = "binary"
    ARCHIVE = "archive"


class VersionStrategy(str, Enum):
    """Enumeration of version strategies."""

    SEMVER = "semver"
    NONE = "none"
    CUSTOM = "custom"
    UNKNOWN = "unknown"
    OTHER = "other"


class SecretKind(str, Enum):
    """Enumeration of secret kinds."""

    REMOTE_JWT = "remote_jwt"
    REMOTE_API_KEY = "remote_api_key"
    GENERATED_STRING = "generated_string"
    CUSTOM = "custom"
    DYNAMIC = "dynamic"
    PRIVATE_KEY = "private_key"
    PUBLIC_KEY = "public_key"
    SECRET_KEY = "secret_key"
    API_KEY = "api_key"
    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
    PASSWORD = "password"
    DATABASE_PASSWORD = "database_password"
    UNKNOWN = "unknown"
    OTHER = "other"


class VariableKind(str, Enum):
    """Enumeration of variable kinds."""

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    CUSTOM = "custom"
    UNKNOWN = "unknown"
    OTHER = "other"


class CICDPlatform(str, Enum):
    """Enumeration of CI/CD platforms."""

    GITHUB = "GitHub"
    GITLAB = "GitLab"
    CIRCLECI = "CircleCI"
    JENKINS = "Jenkins"
    JX = "jx"
    TEKTON = "tekton"
    CUSTOM = "custom"
    NONE = "none"
    UNKNOWN = "unknown"
    OTHER = "other"


class DeploymentStrategy(str, Enum):
    """Enumeration of deployment strategies."""

    BLUE_GREEN = "blue/green"
    ROLLING = "rolling"
    MANUAL = "manual"
    GITOPS = "gitops"
    PIPELINE = "pipeline"
    CUSTOM = "custom"
    NONE = "none"
    UNKNOWN = "unknown"
    OTHER = "other"


class ProvisioningTool(str, Enum):
    """Enumeration of provisioning tools."""

    TERRAFORM = "Terraform"
    CLOUDFORMATION = "CloudFormation"
    CDKTF = "CDKTF"
    AWS_CDK = "AWS CDK"
    BICEP = "Bicep"
    CUSTOM = "custom"
    NONE = "none"
    UNKNOWN = "unknown"
    OTHER = "other"


class Hosting(str, Enum):
    """Enumeration of hosting options."""

    EC2 = "EC2"
    VMWARE = "VMware"
    ORACLE = "Oracle"
    KUBERNETES = "Kubernetes"
    VERCEL = "Vercel"
    ECS = "ECS"
    AWS_LAMBDA = "AWS Lambda"
    AWS_FARGATE = "AWS Fargate"
    AWS_EKS = "AWS EKS"
    AWS_ECS = "AWS ECS"
    AWS_ECS_FARGATE = "AWS ECS Fargate"
    AWS_ECS_FARGATE_SPOT = "AWS ECS Fargate Spot"
    AWS_ECS_FARGATE_SPOT_SPOT = "AWS ECS Fargate Spot Spot"
    ELASTIC_BEANSTALK = "Elastic Beanstalk"
    AZURE_APP_SERVICE = "Azure App Service"
    AZURE_FUNCTIONS = "Azure Functions"
    AZURE_CONTAINER_INSTANCES = "Azure Container Instances"
    AZURE_CONTAINER_APPS = "Azure Container Apps"
    AZURE_CONTAINER_APPS_ENVIRONMENT = "Azure Container Apps Environment"
    AZURE_CONTAINER_APPS_ENVIRONMENT_SERVICE = (
        "Azure Container Apps Environment Service"
    )
    AZURE_CONTAINER_APPS_ENVIRONMENT_SERVICE_SERVICE = (
        "Azure Container Apps Environment Service Service"
    )
    CUSTOM = "custom"
    NONE = "none"
    UNKNOWN = "unknown"


class LoggingProvider(str, Enum):
    """Enumeration of logging providers."""

    CONSOLE = "console"
    CLOUDWATCH = "cloudwatch"
    ELK = "elk"
    SENTRY = "sentry"
    CUSTOM = "custom"
    NONE = "none"
    UNKNOWN = "unknown"
    OTHER = "other"


class MonitoringProvider(str, Enum):
    """Enumeration of monitoring providers."""

    PROMETHEUS = "prometheus"
    DATADOG = "datadog"
    GRAFANA = "grafana"
    SENTRY = "sentry"
    CUSTOM = "custom"
    NONE = "none"
    UNKNOWN = "unknown"
    OTHER = "other"


class AlertingChannelType(str, Enum):
    """Enumeration of alerting channel types."""

    SLACK = "slack"
    TEAMS = "teams"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    CUSTOM = "custom"
    UNKNOWN = "unknown"
    OTHER = "other"


class ComponentKind(str, Enum):
    """Enumeration of component kinds."""

    ENTRY_POINT = "entry_point"


class DependencyKind(str, Enum):
    """Enumeration of dependency kinds."""

    DOCKER_IMAGE = "docker_image"
    REPOSITORY = "repository"
    UNKNOWN = "unknown"
    OTHER = "other"


class Maintainer(BaseModel):
    """Model for project maintainer information."""

    name: str = Field(..., description="Maintainer name")
    email: str = Field(..., description="Maintainer email")
    role: str = Field(..., description="Maintainer role")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class License(BaseModel):
    """Model for project license information."""

    kind: LicenseKind = Field(..., description="License type")
    file: str = Field(default="", description="License file path")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class Tasker(BaseModel):
    """Model for task management tools."""

    kind: TaskerKind = Field(..., description="Tasker type")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class BranchNaming(BaseModel):
    """Model for branch naming patterns."""

    kind: BranchStrategy = Field(..., description="Branch strategy")
    pattern: str = Field(..., description="Branch naming pattern")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class Branch(BaseModel):
    """Model for branch information."""

    name: str = Field(..., description="Branch name")
    environment: Optional[str] = Field(None, description="Environment for this branch")


class Artifact(BaseModel):
    """Model for generated artifacts."""

    type: ArtifactType = Field(..., description="Artifact type")
    definition: str = Field(..., description="Artifact definition")
    location: Union[HttpUrl, str] = Field(..., description="Artifact location")
    version_strategy: VersionStrategy = Field(..., description="Version strategy")

    @field_serializer("location")
    def serialize_location(self, location: Union[HttpUrl, str], _info: Any) -> str:
        """Serialize location to string."""
        return str(location)

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class Secret(BaseModel):
    """Model for secret definitions."""

    name: str = Field(..., description="Secret name")
    kind: SecretKind = Field(..., description="Secret type")
    ref: str = Field(..., description="Secret reference")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class Variable(BaseModel):
    """Model for variable definitions."""

    name: str = Field(..., description="Variable name")
    kind: VariableKind = Field(..., description="Variable type")
    ref: str = Field(..., description="Variable reference")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class Pipeline(BaseModel):
    """Model for CI/CD pipeline."""

    name: str = Field(..., description="Pipeline name")
    ref: str = Field(..., description="Pipeline reference")
    variables: Optional[List[str]] = Field(None, description="Pipeline variables")

    @field_validator("variables", mode="before")
    def validate_variables(cls, v: Any) -> Any:
        """Validate variables field."""
        if v is None:
            return []
        return v

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class CICD(BaseModel):
    """Model for CI/CD configuration."""

    platform: CICDPlatform = Field(..., description="CI/CD platform")
    pipelines: List[Pipeline] = Field(..., description="List of pipelines")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class Environment(BaseModel):
    """Model for deployment environment."""

    name: str = Field(..., description="Environment name")
    url: Optional[HttpUrl] = Field(None, description="Environment URL")

    @field_serializer("url")
    def serialize_url(self, url: Optional[HttpUrl], _info: Any) -> Optional[str]:
        """Serialize URL to string."""
        return str(url) if url else None

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class Infrastructure(BaseModel):
    """Model for infrastructure configuration."""

    provisioning_tool: ProvisioningTool = Field(..., description="Provisioning tool")
    hosting: Hosting = Field(..., description="Hosting platform")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class Deployment(BaseModel):
    """Model for deployment configuration."""

    strategy: DeploymentStrategy = Field(..., description="Deployment strategy")
    environments: Optional[List[Environment]] = Field(
        None, description="Deployment environments"
    )
    infrastructure: Optional[Infrastructure] = Field(
        None, description="Infrastructure configuration"
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class AlertingChannel(BaseModel):
    """Model for alerting channel."""

    name: str = Field(..., description="Alerting channel name")
    type: AlertingChannelType = Field(..., description="Alerting channel type")
    url: Union[HttpUrl, str] = Field(..., description="Alerting channel URL")

    @field_serializer("url")
    def serialize_url(self, url: Union[HttpUrl, str], _info: Any) -> str:
        """Serialize URL to string."""
        return str(url)

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class Dashboard(BaseModel):
    """Model for monitoring dashboard."""

    name: str = Field(..., description="Dashboard name")
    tool: str = Field(..., description="Dashboard tool")
    url: HttpUrl = Field(..., description="Dashboard URL")

    @field_serializer("url")
    def serialize_url(self, url: HttpUrl, _info: Any) -> str:
        """Serialize URL to string."""
        return str(url)

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class Observability(BaseModel):
    """Model for observability configuration."""

    logging_provider: Optional[LoggingProvider] = Field(
        None, description="Logging provider"
    )
    monitoring_providers: Optional[List[MonitoringProvider]] = Field(
        None, description="Monitoring providers"
    )
    alerting_channels: Optional[List[AlertingChannel]] = Field(
        None, description="Alerting channels"
    )
    dashboards: Optional[List[Dashboard]] = Field(
        None, description="Monitoring dashboards"
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class Visibility(str, Enum):
    """Enumeration of repository visibility types."""

    PUBLIC = "public"
    PRIVATE = "private"
    INTERNAL = "internal"


class ProjectType(str, Enum):
    """Enumeration of project types."""

    APPLICATION = "application"
    LIBRARY = "library"
    MICROSERVICE = "microservice"
    CLI = "cli"
    IAC = "iac"
    CONFIG = "config"
    DATA_SCIENCE = "data-science"
    PLUGIN = "plugin"
    TEMPLATE = "template"
    DOCS = "docs"
    TEST = "test"
    OTHER = "other"


class ProjectDomain(str, Enum):
    """Enumeration of project domains."""

    WEB = "web"
    MOBILE = "mobile"
    DEVOPS = "devops"
    ML = "ml"
    DATABASE = "database"
    SECURITY = "security"
    FINANCE = "finance"
    GAMING = "gaming"
    IOT = "iot"
    AGENT = "agent"
    OTHER = "other"
    DOCUMENTATION = "documentation"
    TEST = "test"
    PLUGIN = "plugin"
    TEMPLATE = "template"
    CONFIG = "config"
    DATA_SCIENCE = "data-science"
    MICROSERVICE = "microservice"
    CLI = "cli"


class BuildTool(str, Enum):
    """Enumeration of build tools."""

    MAKE = "make"
    CMAKE = "cmake"
    BAZEL = "bazel"
    NONE = "none"


class LicenseType(str, Enum):
    """Enumeration of license types."""

    MIT = "MIT"
    APACHE_2_0 = "Apache-2.0"
    PROPRIETARY = "proprietary"


class Owner(BaseModel):
    """Model for repository owner information."""

    org: str = Field(..., description="Organization name")
    team: str = Field(..., description="Team name")
    contact: str = Field(..., description="Contact email")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class Language(BaseModel):
    """Model for project language information."""

    primary: str = Field(..., description="Primary programming language")
    secondary: Optional[List[str]] = Field(
        None, description="Secondary programming languages"
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class Project(BaseModel):
    """Model for project information."""

    type: ProjectType = Field(..., description="Project type")
    domain: ProjectDomain = Field(..., description="Project domain")
    language: Language = Field(..., description="Language information")
    framework: Optional[List[str]] = Field(None, description="Frameworks used")
    package_managers: Optional[List[str]] = Field(
        None, description="Package managers used"
    )
    build_tool: Optional[BuildTool] = Field(None, description="Build tool used")
    deploy_targets: Optional[List[str]] = Field(None, description="Deployment targets")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class RepoMetadata(BaseModel):
    """Model for repository metadata."""

    tags: Optional[List[str]] = Field(None, description="Repository tags")
    created_at: Optional[datetime] = Field(None, description="Repository creation date")
    last_commit_at: Optional[datetime] = Field(None, description="Last commit date")
    default_branch: Optional[str] = Field(None, description="Default branch name")
    topics: Optional[List[str]] = Field(None, description="Repository topics")
    forked_from: Optional[Union[HttpUrl, str]] = Field(
        None, description="Forked from repository URL"
    )
    archived: Optional[bool] = Field(
        False, description="Whether repository is archived"
    )
    template: Optional[bool] = Field(
        False, description="Whether repository is a template"
    )
    has_ci: Optional[bool] = Field(False, description="Whether repository has CI/CD")
    has_tests: Optional[bool] = Field(False, description="Whether repository has tests")
    has_docs: Optional[bool] = Field(
        False, description="Whether repository has documentation"
    )
    has_docker: Optional[bool] = Field(
        False, description="Whether repository has Docker configuration"
    )
    has_iac: Optional[bool] = Field(
        False, description="Whether repository has Infrastructure as Code"
    )

    @field_serializer("forked_from")
    def serialize_forked_from(
        self, forked_from: Optional[Union[HttpUrl, str]], _info: Any
    ) -> Optional[str]:
        """Serialize forked_from to string."""
        return str(forked_from) if forked_from else None

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class CommitFrequency(str, Enum):
    """Enumeration of commit frequency types."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    UNKNOWN = "unknown"


class PullRequests(BaseModel):
    """Model for pull request metrics."""

    open: int = Field(..., description="Number of open pull requests")
    merged_last_30d: int = Field(
        ..., description="Number of pull requests merged in last 30 days"
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class Metrics(BaseModel):
    """Model for repository metrics."""

    stars: int = Field(..., description="Number of stars")
    forks: int = Field(..., description="Number of forks")
    open_issues: int = Field(..., description="Number of open issues")
    pull_requests: PullRequests = Field(..., description="Pull request metrics")
    contributors: int = Field(..., description="Number of contributors")
    commit_frequency: CommitFrequency = Field(..., description="Commit frequency")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


# New configuration models for AppConfig
class MetagitConfig(BaseModel):
    """Main model for .metagit.yml configuration file."""

    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(
        default="No description", description="Project description"
    )
    url: Optional[Union[HttpUrl, GitUrl]] = Field(None, description="Project URL")
    kind: Optional[ProjectKind] = Field(
        default=ProjectKind.APPLICATION,
        description="Project kind. This is used to determine the type of project and the best way to manage it.",
    )
    documentation: Optional[List[str]] = Field(
        None, description="Documentation URLs or paths used by the project."
    )
    license: Optional[License] = Field(None, description="License information")
    maintainers: Optional[List[Maintainer]] = Field(
        None, description="Project maintainers"
    )
    branch_strategy: Optional[BranchStrategy] = Field(
        default="unknown", description="Branch strategy used by the project."
    )
    taskers: Optional[List[Tasker]] = Field(
        None, description="Task management tools employed by the project."
    )
    branch_naming: Optional[List[BranchNaming]] = Field(
        None, description="Branch naming patterns used by the project."
    )
    artifacts: Optional[List[Artifact]] = Field(
        default_factory=lambda: [], description="Generated artifacts from the project."
    )
    secrets_management: Optional[List[str]] = Field(
        None, description="Secrets management tools employed by the project."
    )
    secrets: Optional[List[Secret]] = Field(None, description="Secret definitions")
    variables: Optional[List[Variable]] = Field(
        None, description="Variable definitions"
    )
    cicd: Optional[CICD] = Field(None, description="CI/CD configuration")
    deployment: Optional[Deployment] = Field(
        None, description="Deployment configuration"
    )
    observability: Optional[Observability] = Field(
        None, description="Observability configuration"
    )
    paths: Optional[List[ProjectPath]] = Field(
        default_factory=lambda: [],
        description="Important local project paths. In a monorepo, this would include any sub-projects typically found being built in the CICD pipelines.",
    )
    dependencies: Optional[List[ProjectPath]] = Field(
        default_factory=lambda: [],
        description="Additional project dependencies not found in the paths or components lists. These include docker images, helm charts, or terraform modules.",
    )
    components: Optional[List[ProjectPath]] = Field(
        None,
        description="Additional project component paths that may be useful in other projects.",
    )
    workspace: Optional[Workspace] = Field(
        default_factory=lambda: Workspace(
            projects=[
                WorkspaceProject(
                    name="default",
                    repos=[],
                )
            ],
        ),
        description="Workspaces are a collection of projects that are related to each other. They are used to group projects together for a specific purpose. These are manually defined by the user. The internal workspace name is reservice",
    )

    @field_serializer("url")
    def serialize_url(
        self, url: Optional[Union[HttpUrl, str]], _info: Any
    ) -> Optional[str]:
        """Serialize URL to string."""
        return str(url) if url else None

    @property
    def local_workspace_project(self) -> WorkspaceProject:
        """Get the local workspace project configuration."""
        # Combine paths and dependencies into a single list of repos
        repos = []
        if self.paths:
            repos.extend(self.paths)
        if self.dependencies:
            repos.extend(self.dependencies)
        return WorkspaceProject(name="local", repos=repos)

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        validate_assignment = True
        extra = "forbid"


class TenantConfig(AppConfig):
    """Model for tenant configuration that inherits from AppConfig to include all Boundary settings."""

    # Tenant-specific fields (in addition to all AppConfig fields)
    enabled: bool = Field(default=False, description="Whether multi-tenancy is enabled")
    default_tenant: str = Field(default="default", description="Default tenant ID")
    tenant_header: str = Field(default="X-Tenant-ID", description="Tenant header name")
    tenant_required: bool = Field(
        default=False, description="Whether tenant is required"
    )
    allowed_tenants: List[str] = Field(
        default_factory=list, description="List of allowed tenant IDs"
    )

    @classmethod
    def _override_from_environment(cls, config: "TenantConfig") -> "TenantConfig":
        """
        Override configuration with environment variables, including tenant-specific ones.

        Args:
            config: TenantConfig to override

        Returns:
            Updated TenantConfig
        """
        # Call parent method first
        config = super()._override_from_environment(config)

        # Tenant-specific environment variables
        if os.getenv("METAGIT_TENANT_ENABLED"):
            config.enabled = os.getenv("METAGIT_TENANT_ENABLED").lower() == "true"
        if os.getenv("METAGIT_TENANT_DEFAULT"):
            config.default_tenant = os.getenv("METAGIT_TENANT_DEFAULT")
        if os.getenv("METAGIT_TENANT_HEADER"):
            config.tenant_header = os.getenv("METAGIT_TENANT_HEADER")
        if os.getenv("METAGIT_TENANT_REQUIRED"):
            config.tenant_required = (
                os.getenv("METAGIT_TENANT_REQUIRED").lower() == "true"
            )
        if os.getenv("METAGIT_TENANT_ALLOWED"):
            config.allowed_tenants = os.getenv("METAGIT_TENANT_ALLOWED").split(",")

        return config

    @classmethod
    def load(cls, config_path: str = None) -> Union["TenantConfig", Exception]:
        """
        Load TenantConfig from file.

        Args:
            config_path: Path to configuration file (optional)

        Returns:
            TenantConfig object or Exception
        """
        try:
            if not config_path:
                config_path = os.path.join(
                    Path.home(), ".config", "metagit", "config.yml"
                )

            config_file = Path(config_path)
            if not config_file.exists():
                return cls()

            with config_file.open("r") as f:
                config_data = yaml.safe_load(f)

            if "config" in config_data:
                config = cls(**config_data["config"])
            else:
                config = cls(**config_data)

            # Override with environment variables
            config = cls._override_from_environment(config)

            return config

        except Exception as e:
            return e

    class Config:
        """Pydantic configuration."""

        extra = "forbid"

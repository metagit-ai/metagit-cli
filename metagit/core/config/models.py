#!/usr/bin/env python
"""
Pydantic models for .metagit.yml configuration file.

This module defines the data models used to parse and validate
the .metagit.yml configuration file structure.
"""

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl, field_serializer, field_validator


class ProjectKind(str, Enum):
    """Enumeration of project kinds."""

    MONOREPO = "monorepo"
    UMBRELLA = "umbrella"
    APPLICATION = "application"
    GITOPS = "gitops"
    INFRASTRUCTURE = "infrastructure"
    SERVICE = "service"
    LIBRARY = "library"
    WEBSITE = "website"
    OTHER = "other"
    DOCKER_IMAGE = "docker_image"
    REPOSITORY = "repository"


class LicenseKind(str, Enum):
    """Enumeration of license kinds."""

    NONE = "None"
    MIT = "MIT"
    APACHE_2_0 = "Apache-2.0"
    GPL_3_0 = "GPL-3.0"
    BSD_3_CLAUSE = "BSD-3-Clause"
    # Add more as needed


class BranchStrategy(str, Enum):
    """Enumeration of branch strategies."""

    TRUNK = "trunk"
    GITFLOW = "gitflow"
    GITHUBFLOW = "githubflow"
    GITLABFLOW = "gitlabflow"
    FORK = "fork"


class TaskerKind(str, Enum):
    """Enumeration of tasker kinds."""

    TASKFILE = "Taskfile"
    MAKEFILE = "Makefile"
    JEST = "Jest"
    NPM = "NPM"
    ATMOS = "Atmos"


class ArtifactType(str, Enum):
    """Enumeration of artifact types."""

    DOCKER = "docker"
    GITHUB_RELEASE = "github_release"
    STATIC_WEBSITE = "static_website"


class VersionStrategy(str, Enum):
    """Enumeration of version strategies."""

    SEMVER = "semver"
    NONE = "none"


class SecretKind(str, Enum):
    """Enumeration of secret kinds."""

    REMOTE_JWT = "remote_jwt"
    REMOTE_API_KEY = "remote_api_key"
    GENERATED_STRING = "generated_string"


class VariableKind(str, Enum):
    """Enumeration of variable kinds."""

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"


class CICDPlatform(str, Enum):
    """Enumeration of CI/CD platforms."""

    GITHUB = "GitHub"
    GITLAB = "GitLab"
    CIRCLECI = "CircleCI"
    JENKINS = "Jenkins"
    JX = "jx"


class DeploymentStrategy(str, Enum):
    """Enumeration of deployment strategies."""

    BLUE_GREEN = "blue/green"
    ROLLING = "rolling"
    MANUAL = "manual"
    GITOPS = "gitops"
    PIPELINE = "pipeline"


class ProvisioningTool(str, Enum):
    """Enumeration of provisioning tools."""

    TERRAFORM = "Terraform"
    CLOUDFORMATION = "CloudFormation"


class Hosting(str, Enum):
    """Enumeration of hosting options."""

    EC2 = "EC2"
    KUBERNETES = "Kubernetes"
    VERCEL = "Vercel"


class LoggingProvider(str, Enum):
    """Enumeration of logging providers."""

    CONSOLE = "console"
    CLOUDWATCH = "cloudwatch"
    ELK = "elk"
    SENTRY = "sentry"


class MonitoringProvider(str, Enum):
    """Enumeration of monitoring providers."""

    PROMETHEUS = "prometheus"
    DATADOG = "datadog"
    GRAFANA = "grafana"
    NEWRELIC = "newrelic"
    SENTRY = "sentry"


class AlertingChannelType(str, Enum):
    """Enumeration of alerting channel types."""

    SLACK = "slack"
    TEAMS = "teams"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"


class ComponentKind(str, Enum):
    """Enumeration of component kinds."""

    ENTRY_POINT = "entry_point"


class DependencyKind(str, Enum):
    """Enumeration of dependency kinds."""

    DOCKER_IMAGE = "docker_image"
    REPOSITORY = "repository"


class Maintainer(BaseModel):
    """Model for project maintainer information."""

    name: str = Field(..., description="Maintainer name")
    email: str = Field(..., description="Maintainer email")
    role: str = Field(..., description="Maintainer role")


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
        """Serialize the location to a string."""
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
    def validate_variables(cls, v):
        """Convert variable dictionaries to strings if needed."""
        if v is None:
            return v
        if isinstance(v, list):
            return [str(var) if isinstance(var, dict) else var for var in v]
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
        """Serialize the URL to a string."""
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
        """Serialize the URL to a string."""
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
        """Serialize the URL to a string."""
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


class ProjectPath(BaseModel):
    """Model for project path, dependency, component, or workspace project information."""

    name: str = Field(..., description="Project path name")
    description: Optional[str] = Field(None, description="Project description")
    kind: Optional[ProjectKind] = Field(None, description="Project kind")
    ref: Optional[str] = Field(
        None,
        description="Reference in the current project for the target project, used in dependencies",
    )
    path: Optional[str] = Field(None, description="Project path")
    branches: Optional[List[str]] = Field(None, description="Project branches")
    url: Optional[HttpUrl] = Field(None, description="Project URL")
    sync: Optional[bool] = Field(None, description="Sync setting")
    language: Optional[str] = Field(None, description="Programming language")
    language_version: Optional[Union[str, float, int]] = Field(
        None, description="Language version"
    )
    package_manager: Optional[str] = Field(None, description="Package manager")
    frameworks: Optional[List[str]] = Field(None, description="Frameworks used")

    @field_validator("language_version", mode="before")
    def validate_language_version(cls, v):
        """Convert language version to string."""
        if v is None:
            return v
        return str(v)

    @field_serializer("url")
    def serialize_url(self, url: Optional[HttpUrl], _info: Any) -> Optional[str]:
        """Serialize the URL to a string."""
        return str(url) if url else None

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class WorkspaceProject(BaseModel):
    """Model for workspace project."""

    name: str = Field(..., description="Workspace project name")
    repos: List[ProjectPath] = Field(..., description="Repository list")

    @field_validator("repos", mode="before")
    def validate_repos(cls, v):
        """Handle YAML anchors and complex repo structures."""
        if isinstance(v, list):
            # Flatten any nested lists that might come from YAML anchors
            flattened = []
            for item in v:
                if isinstance(item, list):
                    flattened.extend(item)
                else:
                    flattened.append(item)
            return flattened
        return v

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        extra = "forbid"


class Workspace(BaseModel):
    """Model for workspace configuration."""

    projects: List[WorkspaceProject] = Field(..., description="Workspace projects")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class MetagitConfig(BaseModel):
    """Main model for .metagit.yml configuration file."""

    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    url: Optional[HttpUrl] = Field(None, description="Project URL")
    kind: Optional[ProjectKind] = Field(None, description="Project kind")
    documentation: Optional[List[str]] = Field(
        None, description="Documentation URLs or paths"
    )
    license: Optional[License] = Field(None, description="License information")
    maintainers: Optional[List[Maintainer]] = Field(
        None, description="Project maintainers"
    )
    branch_strategy: Optional[BranchStrategy] = Field(
        None, description="Branch strategy"
    )
    taskers: Optional[List[Tasker]] = Field(None, description="Task management tools")
    branches: Optional[List[Branch]] = Field(None, description="Release branches")
    branch_naming: Optional[List[BranchNaming]] = Field(
        None, description="Branch naming patterns"
    )
    branch: Optional[str] = Field(None, description="Current branch")
    checksum: Optional[str] = Field(None, description="Branch checksum")
    last_updated: Optional[datetime] = Field(None, description="Last updated timestamp")
    artifacts: Optional[List[Artifact]] = Field(None, description="Generated artifacts")
    secrets_management: Optional[List[str]] = Field(
        None, description="Secrets management tools"
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
    paths: Optional[List[ProjectPath]] = Field(None, description="Project paths")
    dependencies: Optional[List[ProjectPath]] = Field(
        None, description="Project dependencies"
    )
    components: Optional[List[ProjectPath]] = Field(
        None, description="Project components"
    )
    workspace: Optional[Workspace] = Field(None, description="Workspace configuration")

    @field_serializer("url")
    def serialize_url(
        self, url: Optional[Union[HttpUrl, str]], _info: Any
    ) -> Optional[str]:
        """Serialize the URL to a string."""
        return str(url) if url else None

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        validate_assignment = True
        extra = "forbid"

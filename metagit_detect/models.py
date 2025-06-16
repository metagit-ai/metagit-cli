#!/usr/bin/env python


from pydantic import BaseModel, Field


class DocumentationModel(BaseModel):
    documentation: list[str] = Field(
        default_factory=list, description="List of documentation files or URLs."
    )


class MaintainerModel(BaseModel):
    name: str = ""
    email: str = ""
    role: str = ""


class BranchModel(BaseModel):
    name: str
    release: bool | None = False
    environment: str | None = None
    description: str | None = None


class ConfigFileModel(BaseModel):
    path: str = ""
    format: str = ""
    purpose: str = ""


class EnvironmentVariableModel(BaseModel):
    name: str = ""
    required: bool = True
    description: str = ""


class ConfigurationModel(BaseModel):
    config_files: list[ConfigFileModel] = Field(default_factory=list)
    secrets_management: str = ""
    environment_variables: list[EnvironmentVariableModel] = Field(default_factory=list)


class EntryPointModel(BaseModel):
    path: str = ""
    description: str = ""


class ArchitectureModel(BaseModel):
    type: str = ""
    entry_points: list[EntryPointModel] = Field(default_factory=list)


class ArtifactModel(BaseModel):
    type: str = ""
    definition: str = ""
    location: str = ""
    version_strategy: str = ""


class CICDModel(BaseModel):
    platform: str = ""
    artifacts: list[ArtifactModel] = Field(default_factory=list)


class EnvironmentModel(BaseModel):
    name: str = ""
    url: str = ""
    region: str = ""
    auth_required: bool = True


class InfrastructureModel(BaseModel):
    provisioning_tool: str = ""
    hosting: str = ""


class DeploymentModel(BaseModel):
    strategy: str = ""
    environments: list[EnvironmentModel] = Field(default_factory=list)
    infrastructure: InfrastructureModel = Field(default_factory=InfrastructureModel)


class LoggingModel(BaseModel):
    provider: str = ""
    log_levels: list[str] = Field(default_factory=list)


class AlertingChannelModel(BaseModel):
    name: str = ""
    type: str = ""


class MonitoringModel(BaseModel):
    tools: list[str] = Field(default_factory=list)
    alerting_channels: list[AlertingChannelModel] = Field(default_factory=list)


class DashboardModel(BaseModel):
    name: str = ""
    tool: str = ""
    url: str = ""


class ObservabilityModel(BaseModel):
    logging: LoggingModel = Field(default_factory=LoggingModel)
    monitoring: MonitoringModel = Field(default_factory=MonitoringModel)
    dashboards: list[DashboardModel] = Field(default_factory=list)


class TaskModel(BaseModel):
    kind: str
    path: str


class ProjectPathModel(BaseModel):
    name: str
    path: str | None = None
    url: str | None = None
    description: str | None = None
    language: str | None = None
    language_version: str | float | None = None
    package_manager: str | None = None
    frameworks: list[str] = Field(default_factory=list)
    tasks: list[TaskModel] = Field(default_factory=list)


class ComponentModel(BaseModel):
    name: str
    path: str
    description: str
    language: str
    language_version: str | float


class MetagitConfigModel(BaseModel):
    name: str
    description: str | None = None
    url: str | None = None
    kind: str | None = None
    branch: str | None = None
    checksum: str | int | None = None
    last_updated: str | None = None
    documentation: list[str] = Field(default_factory=list)
    license: str | None = None
    maintainers: list[MaintainerModel] = Field(default_factory=list)
    branch_strategy: str | None = None
    branch_count: int | None = None
    branches: list[BranchModel] = Field(default_factory=list)
    configuration: ConfigurationModel | None = None
    architecture: ArchitectureModel | None = None
    ci_cd: CICDModel | None = None
    deployment: DeploymentModel | None = None
    observability: ObservabilityModel | None = None
    paths: list[ProjectPathModel] = Field(default_factory=list)
    components: list[ComponentModel] = Field(default_factory=list)
    workspace: list[ProjectPathModel] = Field(default_factory=list)

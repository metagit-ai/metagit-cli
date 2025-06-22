#!/usr/bin/env python
"""
Project package for metagit.

This package provides Pydantic models and methods for parsing and validating
.metagit.yml configuration files.
"""

__all__ = [
    # Main configuration model
    "ConfigManager",
    "MetagitConfig",
    # Enums
    "ProjectKind",
    "LicenseKind",
    "BranchStrategy",
    "TaskerKind",
    "ArtifactType",
    "VersionStrategy",
    "SecretKind",
    "VariableKind",
    "CICDPlatform",
    "DeploymentStrategy",
    "ProvisioningTool",
    "Hosting",
    "LoggingProvider",
    "MonitoringProvider",
    "AlertingChannelType",
    "ComponentKind",
    "DependencyKind",
    # Models
    "Maintainer",
    "License",
    "Tasker",
    "BranchNaming",
    "Branch",
    "Artifact",
    "Secret",
    "Variable",
    "Pipeline",
    "CICD",
    "Environment",
    "Infrastructure",
    "Deployment",
    "AlertingChannel",
    "Dashboard",
    "Observability",
    "ProjectPath",
    "Dependency",
    "Component",
    "WorkspaceProject",
    "Workspace",
]

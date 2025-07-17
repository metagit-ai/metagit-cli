#!/usr/bin/env python
"""
Unit tests for metagit.core.config.models
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from metagit.core.config import models


def test_license_kind_enum():
    assert models.LicenseKind.MIT == "MIT"
    assert models.LicenseKind.NONE == "None"


def test_branch_strategy_enum():
    assert models.BranchStrategy.TRUNK == "trunk"
    assert models.BranchStrategy.GITFLOW == "gitflow"


def test_license_model():
    lic = models.License(kind=models.LicenseKind.MIT, file="LICENSE")
    assert lic.kind == models.LicenseKind.MIT
    assert lic.file == "LICENSE"
    with pytest.raises(ValidationError):
        models.License(kind="INVALID", file="LICENSE")


def test_branch_naming_model():
    bn = models.BranchNaming(kind=models.BranchStrategy.TRUNK, pattern="main/*")
    assert bn.kind == models.BranchStrategy.TRUNK
    assert bn.pattern == "main/*"


def test_artifact_model():
    art = models.Artifact(
        type=models.ArtifactType.DOCKER,
        definition="Dockerfile",
        location="http://example.com/image",
        version_strategy=models.VersionStrategy.SEMVER,
    )
    assert art.type == models.ArtifactType.DOCKER
    assert art.location == "http://example.com/image"
    assert art.version_strategy == models.VersionStrategy.SEMVER


def test_secret_model():
    sec = models.Secret(
        name="API_KEY", kind=models.SecretKind.REMOTE_API_KEY, ref="env:API_KEY"
    )
    assert sec.name == "API_KEY"
    assert sec.kind == models.SecretKind.REMOTE_API_KEY
    assert sec.ref == "env:API_KEY"


def test_variable_model():
    var = models.Variable(
        name="DEBUG", kind=models.VariableKind.BOOLEAN, ref="env:DEBUG"
    )
    assert var.name == "DEBUG"
    assert var.kind == models.VariableKind.BOOLEAN
    assert var.ref == "env:DEBUG"


def test_pipeline_and_cicd():
    pipe = models.Pipeline(
        name="build", ref=".github/workflows/build.yml", variables=["DEBUG"]
    )
    cicd = models.CICD(platform=models.CICDPlatform.GITHUB, pipelines=[pipe])
    assert cicd.platform == models.CICDPlatform.GITHUB
    assert cicd.pipelines[0].name == "build"


def test_environment_and_deployment():
    env = models.Environment(name="prod", url="http://prod.example.com")
    infra = models.Infrastructure(
        provisioning_tool=models.ProvisioningTool.TERRAFORM, hosting=models.Hosting.EC2
    )
    dep = models.Deployment(
        strategy=models.DeploymentStrategy.ROLLING,
        environments=[env],
        infrastructure=infra,
    )
    assert dep.strategy == models.DeploymentStrategy.ROLLING
    assert dep.environments[0].name == "prod"
    assert dep.infrastructure.hosting == models.Hosting.EC2


def test_observability():
    alert = models.AlertingChannel(
        name="slack", type=models.AlertingChannelType.SLACK, url="http://slack.com"
    )
    dash = models.Dashboard(name="main", tool="grafana", url="http://grafana.com")
    obs = models.Observability(
        logging_provider=models.LoggingProvider.CONSOLE,
        monitoring_providers=[models.MonitoringProvider.PROMETHEUS],
        alerting_channels=[alert],
        dashboards=[dash],
    )
    assert obs.logging_provider == models.LoggingProvider.CONSOLE
    assert obs.monitoring_providers[0] == models.MonitoringProvider.PROMETHEUS
    assert obs.alerting_channels[0].type == models.AlertingChannelType.SLACK
    assert obs.dashboards[0].tool == "grafana"


def test_project_and_metadata():
    lang = models.Language(primary="python", secondary=["js"])
    proj = models.Project(
        type=models.ProjectType.APPLICATION,
        domain=models.ProjectDomain.WEB,
        language=lang,
        framework=["pytest"],
        package_managers=["pip"],
        build_tool=models.BuildTool.MAKE,
        deploy_targets=["prod"],
    )
    assert proj.type == models.ProjectType.APPLICATION
    assert proj.language.primary == "python"
    meta = models.RepoMetadata(tags=["tag1"], created_at=datetime.now())
    assert "tag1" in meta.tags


def test_metrics_and_pull_requests():
    pr = models.PullRequests(open=2, merged_last_30d=5)
    metrics = models.Metrics(
        stars=10,
        forks=2,
        open_issues=1,
        pull_requests=pr,
        contributors=3,
        commit_frequency=models.CommitFrequency.DAILY,
    )
    assert metrics.stars == 10
    assert metrics.pull_requests.open == 2


def test_metagit_config_minimal():
    cfg = models.MetagitConfig(name="proj")
    assert cfg.name == "proj"
    # Test serialization
    assert isinstance(cfg.serialize_url(None, None), type(None))


class TestMetagitConfig:
    """Test MetagitConfig class."""

    def test_metagit_config_basic(self):
        """Test basic MetagitConfig creation."""
        config = models.MetagitConfig(
            name="test-project",
            description="A test project",
            kind=models.ProjectKind.APPLICATION,
        )

        assert config.name == "test-project"
        assert config.description == "A test project"
        assert config.kind == models.ProjectKind.APPLICATION

    def test_metagit_config_with_optional_fields(self):
        """Test MetagitConfig with optional fields."""
        config = models.MetagitConfig(
            name="test-project",
            description="A test project",
            kind=models.ProjectKind.APPLICATION,
            branch_strategy=models.BranchStrategy.TRUNK,
            license={"kind": models.LicenseKind.MIT, "file": "LICENSE"},
        )

        assert config.name == "test-project"
        assert config.branch_strategy == models.BranchStrategy.TRUNK
        assert config.license.kind == models.LicenseKind.MIT
        assert config.license.file == "LICENSE"

    def test_metagit_config_validation_error(self):
        """Test MetagitConfig validation error."""
        with pytest.raises(ValidationError):
            models.MetagitConfig()  # Missing required name field

    def test_metagit_config_does_not_have_detection_attributes(self):
        """Test that MetagitConfig does not have detection-specific attributes."""
        config = models.MetagitConfig(name="test-project")

        # These attributes should not exist on MetagitConfig
        assert not hasattr(config, "branches")
        assert not hasattr(config, "metrics")
        assert not hasattr(config, "metadata")
        assert not hasattr(config, "detection_timestamp")
        assert not hasattr(config, "detection_source")
        assert not hasattr(config, "detection_version")

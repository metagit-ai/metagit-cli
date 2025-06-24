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


class TestMetagitRecord:
    """Test MetagitRecord class."""

    def test_metagit_record_basic(self):
        """Test basic MetagitRecord creation."""
        record = models.MetagitRecord(
            name="test-project",
            description="A test project",
            kind=models.ProjectKind.APPLICATION,
        )

        assert record.name == "test-project"
        assert record.description == "A test project"
        assert record.kind == models.ProjectKind.APPLICATION
        assert record.branches is None
        assert record.metrics is None
        assert record.metadata is None
        assert record.detection_timestamp is None
        assert record.detection_source is None
        assert record.detection_version is None

    def test_metagit_record_with_detection_attributes(self):
        """Test MetagitRecord with detection-specific attributes."""
        timestamp = datetime.now()
        branches = [models.Branch(name="main", environment="production")]
        metrics = models.Metrics(
            stars=100,
            forks=10,
            open_issues=5,
            pull_requests=models.PullRequests(open=3, merged_last_30d=15),
            contributors=8,
            commit_frequency=models.CommitFrequency.DAILY,
        )
        metadata = models.RepoMetadata(
            tags=["python", "api"],
            created_at=timestamp,
            has_ci=True,
            has_tests=True,
        )

        record = models.MetagitRecord(
            name="test-project",
            description="A test project",
            kind=models.ProjectKind.APPLICATION,
            branches=branches,
            metrics=metrics,
            metadata=metadata,
            detection_timestamp=timestamp,
            detection_source="github",
            detection_version="1.0.0",
        )

        assert record.name == "test-project"
        assert record.branches == branches
        assert record.metrics == metrics
        assert record.metadata == metadata
        assert record.detection_timestamp == timestamp
        assert record.detection_source == "github"
        assert record.detection_version == "1.0.0"

    def test_metagit_record_inheritance(self):
        """Test that MetagitRecord properly inherits from MetagitConfig."""
        record = models.MetagitRecord(
            name="test-project",
            description="A test project",
            kind=models.ProjectKind.APPLICATION,
            branch_strategy=models.BranchStrategy.TRUNK,
        )

        # Should have MetagitConfig attributes
        assert record.name == "test-project"
        assert record.description == "A test project"
        assert record.kind == models.ProjectKind.APPLICATION
        assert record.branch_strategy == models.BranchStrategy.TRUNK

        # Should also have MetagitRecord-specific attributes
        assert hasattr(record, "branches")
        assert hasattr(record, "metrics")
        assert hasattr(record, "metadata")
        assert hasattr(record, "detection_timestamp")
        assert hasattr(record, "detection_source")
        assert hasattr(record, "detection_version")

    def test_metagit_record_serialization(self):
        """Test MetagitRecord serialization."""
        timestamp = datetime.now()
        record = models.MetagitRecord(
            name="test-project",
            description="A test project",
            kind=models.ProjectKind.APPLICATION,
            detection_timestamp=timestamp,
            detection_source="github",
            detection_version="1.0.0",
        )

        # Test that it can be serialized to dict
        record_dict = record.model_dump()
        assert record_dict["name"] == "test-project"
        assert record_dict["detection_source"] == "github"
        assert record_dict["detection_version"] == "1.0.0"

    def test_metagit_record_from_config(self):
        """Test creating MetagitRecord from existing MetagitConfig."""
        config = models.MetagitConfig(
            name="test-project",
            description="A test project",
            kind=models.ProjectKind.APPLICATION,
            branch_strategy=models.BranchStrategy.TRUNK,
        )

        # Create record from config
        record = models.MetagitRecord(
            **config.model_dump(),
            detection_timestamp=datetime.now(),
            detection_source="local",
            detection_version="1.0.0",
        )

        assert record.name == config.name
        assert record.description == config.description
        assert record.kind == config.kind
        assert record.branch_strategy == config.branch_strategy
        assert record.detection_source == "local"

    def test_metagit_record_validation_error(self):
        """Test MetagitRecord validation error."""
        with pytest.raises(ValidationError):
            models.MetagitRecord()  # Missing required name field


class TestMetagitRecordDetectionAttributes:
    """Test MetagitRecord detection-specific attributes."""

    def test_branches_attribute(self):
        """Test branches attribute in MetagitRecord."""
        branches = [
            models.Branch(name="main", environment="production"),
            models.Branch(name="develop", environment="development"),
        ]

        record = models.MetagitRecord(
            name="test-project",
            branches=branches,
        )

        assert record.branches == branches
        assert len(record.branches) == 2
        assert record.branches[0].name == "main"
        assert record.branches[1].name == "develop"

    def test_metrics_attribute(self):
        """Test metrics attribute in MetagitRecord."""
        metrics = models.Metrics(
            stars=100,
            forks=10,
            open_issues=5,
            pull_requests=models.PullRequests(open=3, merged_last_30d=15),
            contributors=8,
            commit_frequency=models.CommitFrequency.DAILY,
        )

        record = models.MetagitRecord(
            name="test-project",
            metrics=metrics,
        )

        assert record.metrics == metrics
        assert record.metrics.stars == 100
        assert record.metrics.pull_requests.open == 3
        assert record.metrics.commit_frequency == models.CommitFrequency.DAILY

    def test_metadata_attribute(self):
        """Test metadata attribute in MetagitRecord."""
        timestamp = datetime.now()
        metadata = models.RepoMetadata(
            tags=["python", "api"],
            created_at=timestamp,
            has_ci=True,
            has_tests=True,
            has_docs=True,
        )

        record = models.MetagitRecord(
            name="test-project",
            metadata=metadata,
        )

        assert record.metadata == metadata
        assert record.metadata.tags == ["python", "api"]
        assert record.metadata.has_ci is True
        assert record.metadata.has_tests is True
        assert record.metadata.has_docs is True

    def test_detection_timestamp_attribute(self):
        """Test detection_timestamp attribute in MetagitRecord."""
        timestamp = datetime.now()

        record = models.MetagitRecord(
            name="test-project",
            detection_timestamp=timestamp,
        )

        assert record.detection_timestamp == timestamp

    def test_detection_source_attribute(self):
        """Test detection_source attribute in MetagitRecord."""
        record = models.MetagitRecord(
            name="test-project",
            detection_source="github",
        )

        assert record.detection_source == "github"

    def test_detection_version_attribute(self):
        """Test detection_version attribute in MetagitRecord."""
        record = models.MetagitRecord(
            name="test-project",
            detection_version="1.0.0",
        )

        assert record.detection_version == "1.0.0"


class TestMetagitConfigMetagitRecordSeparation:
    """Test the separation between MetagitConfig and MetagitRecord."""

    def test_config_does_not_have_detection_attributes(self):
        """Test that MetagitConfig does not have detection attributes."""
        config = models.MetagitConfig(name="test-project")

        # These should not be attributes of MetagitConfig
        assert not hasattr(config, "branches")
        assert not hasattr(config, "metrics")
        assert not hasattr(config, "metadata")
        assert not hasattr(config, "detection_timestamp")
        assert not hasattr(config, "detection_source")
        assert not hasattr(config, "detection_version")

    def test_record_has_detection_attributes(self):
        """Test that MetagitRecord has detection attributes."""
        record = models.MetagitRecord(name="test-project")

        # These should be attributes of MetagitRecord
        assert hasattr(record, "branches")
        assert hasattr(record, "metrics")
        assert hasattr(record, "metadata")
        assert hasattr(record, "detection_timestamp")
        assert hasattr(record, "detection_source")
        assert hasattr(record, "detection_version")

    def test_config_save_does_not_include_detection_data(self):
        """Test that MetagitConfig serialization doesn't include detection data."""
        config = models.MetagitConfig(
            name="test-project",
            description="A test project",
            kind=models.ProjectKind.APPLICATION,
        )

        config_dict = config.model_dump()

        # Should not contain detection-specific keys
        assert "branches" not in config_dict
        assert "metrics" not in config_dict
        assert "metadata" not in config_dict
        assert "detection_timestamp" not in config_dict
        assert "detection_source" not in config_dict
        assert "detection_version" not in config_dict

    def test_record_save_includes_detection_data(self):
        """Test that MetagitRecord serialization includes detection data."""
        timestamp = datetime.now()
        record = models.MetagitRecord(
            name="test-project",
            description="A test project",
            kind=models.ProjectKind.APPLICATION,
            detection_timestamp=timestamp,
            detection_source="github",
            detection_version="1.0.0",
        )

        record_dict = record.model_dump()

        # Should contain detection-specific keys
        assert "branches" in record_dict
        assert "metrics" in record_dict
        assert "metadata" in record_dict
        assert "detection_timestamp" in record_dict
        assert "detection_source" in record_dict
        assert "detection_version" in record_dict

        # Should also contain config keys
        assert "name" in record_dict
        assert "description" in record_dict
        assert "kind" in record_dict

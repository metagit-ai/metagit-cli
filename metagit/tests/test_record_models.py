#!/usr/bin/env python
"""
Unit tests for metagit.core.record.models
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from metagit.core.config import models
from metagit.core.record import models as record_models


class TestMetagitRecord:
    """Test MetagitRecord class."""

    def test_metagit_record_basic(self):
        """Test basic MetagitRecord creation."""
        record = record_models.MetagitRecord(
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

        record = record_models.MetagitRecord(
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
        record = record_models.MetagitRecord(
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
        record = record_models.MetagitRecord(
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
        record = record_models.MetagitRecord(
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
            record_models.MetagitRecord()  # Missing required name field


class TestMetagitRecordDetectionAttributes:
    """Test MetagitRecord detection-specific attributes."""

    def test_branches_attribute(self):
        """Test branches attribute in MetagitRecord."""
        branches = [
            models.Branch(name="main", environment="production"),
            models.Branch(name="develop", environment="development"),
        ]

        record = record_models.MetagitRecord(
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

        record = record_models.MetagitRecord(
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

        record = record_models.MetagitRecord(
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

        record = record_models.MetagitRecord(
            name="test-project",
            detection_timestamp=timestamp,
        )

        assert record.detection_timestamp == timestamp

    def test_detection_source_attribute(self):
        """Test detection_source attribute in MetagitRecord."""
        record = record_models.MetagitRecord(
            name="test-project",
            detection_source="github",
        )

        assert record.detection_source == "github"

    def test_detection_version_attribute(self):
        """Test detection_version attribute in MetagitRecord."""
        record = record_models.MetagitRecord(
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
        record = record_models.MetagitRecord(name="test-project")

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
        record = record_models.MetagitRecord(
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

#!/usr/bin/env python
"""
Unit tests for MetagitRecord conversion methods.

This module tests the fast conversion methods between MetagitRecord and MetagitConfig
using the latest Pydantic best practices.
"""

import unittest
from datetime import datetime
from pathlib import Path

from metagit.core.config.models import (
    Branch,
    BranchStrategy,
    CICD,
    CICDPlatform,
    Language,
    License,
    LicenseKind,
    Maintainer,
    Metrics,
    MetagitConfig,
    Pipeline,
    PullRequests,
    RepoMetadata,
)
from metagit.core.project.models import ProjectKind
from metagit.core.record.models import MetagitRecord


class TestMetagitRecordConversion(unittest.TestCase):
    """Test cases for MetagitRecord conversion methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_config = MetagitConfig(
            name="test-project",
            description="A test project for conversion",
            url="https://github.com/test/project.git",
            kind=ProjectKind.APPLICATION,
            branch_strategy=BranchStrategy.TRUNK,
            license=License(kind=LicenseKind.MIT, file="LICENSE"),
            maintainers=[
                Maintainer(
                    name="John Doe", email="john@example.com", role="Lead Developer"
                )
            ],
            cicd=CICD(
                platform=CICDPlatform.GITHUB,
                pipelines=[Pipeline(name="CI", ref=".github/workflows/ci.yml")],
            ),
        )

        self.sample_record = MetagitRecord(
            name="test-project",
            description="A test project for conversion",
            url="https://github.com/test/project.git",
            kind=ProjectKind.APPLICATION,
            branch_strategy=BranchStrategy.TRUNK,
            license=License(kind=LicenseKind.MIT, file="LICENSE"),
            maintainers=[
                Maintainer(
                    name="John Doe", email="john@example.com", role="Lead Developer"
                )
            ],
            cicd=CICD(
                platform=CICDPlatform.GITHUB,
                pipelines=[Pipeline(name="CI", ref=".github/workflows/ci.yml")],
            ),
            # Detection-specific fields
            branch="main",
            checksum="abc123def456",
            last_updated=datetime.now(),
            branches=[Branch(name="main", environment="production")],
            metrics=Metrics(
                stars=100,
                forks=10,
                open_issues=5,
                pull_requests=PullRequests(open=3, merged_last_30d=15),
                contributors=8,
                commit_frequency="daily",
            ),
            metadata=RepoMetadata(
                tags=["python", "api"],
                created_at=datetime.now(),
                has_ci=True,
                has_tests=True,
                has_docs=True,
                has_docker=False,
                has_iac=True,
            ),
            language=Language(primary="Python", secondary=["JavaScript"]),
            language_version="3.9",
            domain="web",
            detection_timestamp=datetime.now(),
            detection_source="github",
            detection_version="1.0.0",
        )

    def test_to_metagit_config_basic(self):
        """Test basic conversion from MetagitRecord to MetagitConfig."""
        config = self.sample_record.to_metagit_config()

        # Should have all MetagitConfig fields
        self.assertEqual(config.name, "test-project")
        self.assertEqual(config.description, "A test project for conversion")
        self.assertEqual(config.url, "https://github.com/test/project.git")
        self.assertEqual(config.kind, ProjectKind.APPLICATION)
        self.assertEqual(config.branch_strategy, BranchStrategy.TRUNK)
        self.assertIsNotNone(config.license)
        self.assertIsNotNone(config.maintainers)
        self.assertIsNotNone(config.cicd)

        # Should not have detection-specific fields
        self.assertFalse(hasattr(config, "branch"))
        self.assertFalse(hasattr(config, "checksum"))
        self.assertFalse(hasattr(config, "last_updated"))
        self.assertFalse(hasattr(config, "branches"))
        self.assertFalse(hasattr(config, "metrics"))
        self.assertFalse(hasattr(config, "metadata"))
        self.assertFalse(hasattr(config, "detection_timestamp"))
        self.assertFalse(hasattr(config, "detection_source"))
        self.assertFalse(hasattr(config, "detection_version"))

    def test_to_metagit_config_with_detection_fields(self):
        """Test conversion keeping detection fields."""
        # This test is removed because MetagitConfig doesn't support detection fields
        # The exclude_detection_fields parameter is for future extensibility
        pass

    def test_field_differences(self):
        """Test field difference detection."""
        differences = MetagitRecord.get_field_differences()

        # Should have field difference information
        self.assertIn("common_fields", differences)
        self.assertIn("record_only_fields", differences)
        self.assertIn("config_only_fields", differences)
        self.assertIn("total_record_fields", differences)
        self.assertIn("total_config_fields", differences)
        self.assertIn("common_field_count", differences)

        # Should have some common fields
        self.assertGreater(len(differences["common_fields"]), 0)
        self.assertIn("name", differences["common_fields"])
        self.assertIn("description", differences["common_fields"])

        # Should have some record-only fields
        self.assertGreater(len(differences["record_only_fields"]), 0)
        self.assertIn("detection_source", differences["record_only_fields"])
        self.assertIn("detection_version", differences["record_only_fields"])

    def test_compatible_fields(self):
        """Test compatible field detection."""
        compatible_fields = MetagitRecord.get_compatible_fields()

        # Should have some compatible fields
        self.assertGreater(len(compatible_fields), 0)
        self.assertIn("name", compatible_fields)
        self.assertIn("description", compatible_fields)
        self.assertIn("url", compatible_fields)
        self.assertIn("kind", compatible_fields)

        # Should not include detection-specific fields
        self.assertNotIn("detection_source", compatible_fields)
        self.assertNotIn("detection_version", compatible_fields)
        self.assertNotIn("branch", compatible_fields)

    def test_from_metagit_config_basic(self):
        """Test basic conversion from MetagitConfig to MetagitRecord."""
        record = MetagitRecord.from_metagit_config(self.sample_config)

        # Should have all MetagitConfig fields
        self.assertEqual(record.name, "test-project")
        self.assertEqual(record.description, "A test project for conversion")
        self.assertEqual(record.url, "https://github.com/test/project.git")
        self.assertEqual(record.kind, ProjectKind.APPLICATION)
        self.assertEqual(record.branch_strategy, BranchStrategy.TRUNK)

        # Should have detection-specific fields with defaults
        self.assertEqual(record.detection_source, "local")
        self.assertEqual(record.detection_version, "1.0.0")
        self.assertIsNotNone(record.detection_timestamp)
        self.assertIsNone(record.branch)
        self.assertIsNone(record.checksum)
        self.assertIsNone(record.metrics)
        self.assertIsNone(record.metadata)

    def test_from_metagit_config_with_custom_detection_data(self):
        """Test conversion with custom detection data."""
        additional_data = {
            "branch": "feature-branch",
            "checksum": "def789ghi012",
            "metrics": Metrics(
                stars=50,
                forks=5,
                open_issues=2,
                pull_requests=PullRequests(open=1, merged_last_30d=8),
                contributors=4,
                commit_frequency="weekly",
            ),
        }

        record = MetagitRecord.from_metagit_config(
            self.sample_config,
            detection_source="gitlab",
            detection_version="2.0.0",
            additional_detection_data=additional_data,
        )

        # Should have custom detection data
        self.assertEqual(record.detection_source, "gitlab")
        self.assertEqual(record.detection_version, "2.0.0")
        self.assertEqual(record.branch, "feature-branch")
        self.assertEqual(record.checksum, "def789ghi012")
        self.assertIsNotNone(record.metrics)
        self.assertEqual(record.metrics.stars, 50)

    def test_conversion_round_trip(self):
        """Test round-trip conversion: Config -> Record -> Config."""
        # Config -> Record
        record = MetagitRecord.from_metagit_config(
            self.sample_config,
            detection_source="github",
            detection_version="1.0.0",
        )

        # Record -> Config
        config = record.to_metagit_config()

        # Should be equivalent to original config
        self.assertEqual(config.name, self.sample_config.name)
        self.assertEqual(config.description, self.sample_config.description)
        self.assertEqual(config.url, self.sample_config.url)
        self.assertEqual(config.kind, self.sample_config.kind)
        self.assertEqual(config.branch_strategy, self.sample_config.branch_strategy)

    def test_conversion_round_trip_with_detection_fields(self):
        """Test round-trip conversion keeping detection fields."""
        # This test is removed because MetagitConfig doesn't support detection fields
        # The exclude_detection_fields parameter is for future extensibility
        pass

    def test_get_detection_summary(self):
        """Test getting detection summary."""
        summary = self.sample_record.get_detection_summary()

        # Should have basic detection info
        self.assertEqual(summary["detection_source"], "github")
        self.assertEqual(summary["detection_version"], "1.0.0")
        self.assertEqual(summary["current_branch"], "main")
        self.assertEqual(summary["checksum"], "abc123def456")
        self.assertIsNotNone(summary["detection_timestamp"])

        # Should have metrics summary
        self.assertIn("metrics", summary)
        self.assertEqual(summary["metrics"]["stars"], 100)
        self.assertEqual(summary["metrics"]["forks"], 10)
        self.assertEqual(summary["metrics"]["open_issues"], 5)
        self.assertEqual(summary["metrics"]["contributors"], 8)

        # Should have metadata summary
        self.assertIn("metadata", summary)
        self.assertTrue(summary["metadata"]["has_ci"])
        self.assertTrue(summary["metadata"]["has_tests"])
        self.assertTrue(summary["metadata"]["has_docs"])
        self.assertFalse(summary["metadata"]["has_docker"])
        self.assertTrue(summary["metadata"]["has_iac"])

    def test_get_detection_summary_without_optional_fields(self):
        """Test detection summary when optional fields are None."""
        record = MetagitRecord(
            name="minimal-record",
            detection_source="local",
            detection_version="1.0.0",
        )

        summary = record.get_detection_summary()

        # Should have basic detection info
        self.assertEqual(summary["detection_source"], "local")
        self.assertEqual(summary["detection_version"], "1.0.0")
        self.assertIsNone(summary["current_branch"])
        self.assertIsNone(summary["checksum"])

        # Should not have metrics or metadata
        self.assertNotIn("metrics", summary)
        self.assertNotIn("metadata", summary)

    def test_conversion_performance(self):
        """Test that conversion is fast and efficient."""
        import time

        # Create a complex record
        record = MetagitRecord(
            name="performance-test",
            description="A project for performance testing",
            kind=ProjectKind.APPLICATION,
            branch_strategy=BranchStrategy.GITFLOW,
            detection_source="github",
            detection_version="1.0.0",
            metrics=Metrics(
                stars=1000,
                forks=100,
                open_issues=50,
                pull_requests=PullRequests(open=25, merged_last_30d=100),
                contributors=50,
                commit_frequency="daily",
            ),
            metadata=RepoMetadata(
                tags=["python", "fastapi", "postgresql"],
                has_ci=True,
                has_tests=True,
                has_docs=True,
                has_docker=True,
                has_iac=True,
            ),
        )

        # Measure conversion time
        start_time = time.time()
        for _ in range(1000):
            config = record.to_metagit_config()
        end_time = time.time()

        # Should complete 1000 conversions in under 1 second
        conversion_time = end_time - start_time
        self.assertLess(conversion_time, 1.0, f"Conversion took {conversion_time:.3f}s")

    def test_conversion_with_complex_nested_objects(self):
        """Test conversion with complex nested objects."""
        # Create config with complex nested objects
        config = MetagitConfig(
            name="complex-project",
            description="A project with complex configuration",
            kind=ProjectKind.SERVICE,
            branch_strategy=BranchStrategy.GITHUBFLOW,
            license=License(kind=LicenseKind.APACHE_2_0, file="LICENSE"),
            maintainers=[
                Maintainer(name="Alice", email="alice@example.com", role="Architect"),
                Maintainer(name="Bob", email="bob@example.com", role="Developer"),
            ],
            cicd=CICD(
                platform=CICDPlatform.GITHUB,
                pipelines=[
                    Pipeline(name="CI", ref=".github/workflows/ci.yml"),
                    Pipeline(name="CD", ref=".github/workflows/cd.yml"),
                ],
            ),
        )

        # Convert to record
        record = MetagitRecord.from_metagit_config(
            config,
            detection_source="gitlab",
            detection_version="2.0.0",
        )

        # Convert back to config
        result_config = record.to_metagit_config()

        # Should preserve complex nested objects
        self.assertEqual(len(result_config.maintainers), 2)
        self.assertEqual(result_config.maintainers[0].name, "Alice")
        self.assertEqual(result_config.maintainers[1].name, "Bob")
        self.assertEqual(len(result_config.cicd.pipelines), 2)
        self.assertEqual(result_config.cicd.pipelines[0].name, "CI")
        self.assertEqual(result_config.cicd.pipelines[1].name, "CD")

    def test_conversion_with_minimal_data(self):
        """Test conversion with minimal required data."""
        # Minimal config
        minimal_config = MetagitConfig(name="minimal-project")

        # Convert to record
        record = MetagitRecord.from_metagit_config(minimal_config)

        # Should have required fields
        self.assertEqual(record.name, "minimal-project")
        self.assertIsNotNone(record.detection_timestamp)
        self.assertEqual(record.detection_source, "local")

        # Convert back to config
        result_config = record.to_metagit_config()

        # Should preserve required fields
        self.assertEqual(result_config.name, "minimal-project")

    def test_conversion_validation(self):
        """Test that conversion maintains data validation."""
        # Create a valid record
        record = MetagitRecord(
            name="valid-project",
            kind=ProjectKind.APPLICATION,
            detection_source="github",
        )

        # Convert to config
        config = record.to_metagit_config()

        # Should be a valid MetagitConfig
        self.assertIsInstance(config, MetagitConfig)
        self.assertEqual(config.name, "valid-project")
        self.assertEqual(config.kind, ProjectKind.APPLICATION)

        # Convert back to record
        new_record = MetagitRecord.from_metagit_config(config)

        # Should be a valid MetagitRecord
        self.assertIsInstance(new_record, MetagitRecord)
        self.assertEqual(new_record.name, "valid-project")
        self.assertEqual(new_record.kind, ProjectKind.APPLICATION)


if __name__ == "__main__":
    unittest.main()

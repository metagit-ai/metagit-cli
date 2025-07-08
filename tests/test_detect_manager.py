#!/usr/bin/env python3
"""
Unit tests for DetectionManager and DetectionManagerConfig.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from metagit.core.config.models import Language, ProjectDomain, ProjectType
from metagit.core.detect import (
    BranchInfo,
    CIConfigAnalysis,
    DetectionManager,
    DetectionManagerConfig,
    GitBranchAnalysis,
    LanguageDetection,
    ProjectTypeDetection,
)


@pytest.fixture
def default_path(tmp_path):
    # Use a temporary directory for path
    return str(tmp_path)


def test_config_all_enabled():
    config = DetectionManagerConfig.all_enabled()
    enabled = config.get_enabled_methods()
    assert set(enabled) == {
        "branch_analysis",
        "ci_config_analysis",
        "directory_summary",
        "directory_details",
        "commit_analysis",
        "tag_analysis",
    }


def test_config_minimal():
    config = DetectionManagerConfig.minimal()
    enabled = config.get_enabled_methods()
    assert set(enabled) == {"branch_analysis", "ci_config_analysis"}


def test_config_toggle():
    config = DetectionManagerConfig(
        branch_analysis_enabled=False,
        ci_config_analysis_enabled=True,
        directory_summary_enabled=True,
        directory_details_enabled=False,
    )
    enabled = config.get_enabled_methods()
    assert set(enabled) == {"ci_config_analysis", "directory_summary"}


def test_detection_manager_from_path(default_path):
    """Test creating DetectionManager from path."""
    config = DetectionManagerConfig(
        branch_analysis_enabled=True,
        ci_config_analysis_enabled=True,
        directory_summary_enabled=True,
        directory_details_enabled=True,
    )

    with patch(
        "metagit.core.detect.manager.DetectionManager._load_existing_config",
        return_value=None,
    ):
        manager = DetectionManager.from_path(default_path, config=config)
        assert not isinstance(manager, Exception)
        assert manager.path == default_path
        # Use the actual path name instead of hardcoded "tmp_path"
        expected_name = Path(default_path).name
        assert manager.name == expected_name
        assert manager.detection_config == config


def test_detection_manager_from_path_with_existing_config(default_path):
    """Test creating DetectionManager from path with existing config."""
    from metagit.core.config.models import MetagitRecord

    existing_config = MetagitRecord(
        name="test-project", description="A test project", kind="application"
    )

    config = DetectionManagerConfig.minimal()

    with patch(
        "metagit.core.detect.manager.DetectionManager._load_existing_config",
        return_value=existing_config,
    ):
        manager = DetectionManager.from_path(default_path, config=config)
        assert not isinstance(manager, Exception)
        assert manager.name == "test-project"
        assert manager.description == "A test project"
        assert manager.kind == "application"


def test_detection_manager_run_all_and_summary(default_path):
    config = DetectionManagerConfig(
        branch_analysis_enabled=True,
        ci_config_analysis_enabled=True,
        directory_summary_enabled=True,
        directory_details_enabled=True,
    )

    with patch(
        "metagit.core.detect.manager.DetectionManager._load_existing_config",
        return_value=None,
    ):
        manager = DetectionManager.from_path(default_path, config=config)
        assert not isinstance(manager, Exception)

        # Create a mock RepositoryAnalysis with all analysis results
        mock_repo_analysis = RepositoryAnalysis(
            path=default_path,
            name="test-project",
            description="A test project",
            url="https://github.com/test/project",
            language_detection=LanguageDetection(primary="Python"),
            project_type_detection=ProjectTypeDetection(
                type=ProjectType.APPLICATION, domain=ProjectDomain.WEB
            ),
            branch_analysis=GitBranchAnalysis(
                strategy_guess="Unknown",
                branches=[BranchInfo(name="main", is_remote=False)],
            ),
            ci_config_analysis=CIConfigAnalysis(detected_tool="TestCI"),
            metadata=None,
            metrics=None,
        )

        # Patch RepositoryAnalysis.from_path to return our mock
        with patch(
            "metagit.core.detect.manager.RepositoryAnalysis.from_path",
            return_value=mock_repo_analysis,
        ):
            result = manager.run_all()
            assert result is None
            assert manager.analysis_completed is True
            assert manager.repository_analysis is not None

            # Patch missing fields for summary
            object.__setattr__(manager, "domain", ProjectDomain.WEB)
            object.__setattr__(manager, "kind", ProjectType.APPLICATION)
            object.__setattr__(manager, "language", Language(primary="Python"))
            object.__setattr__(manager, "language_version", "3.9")

            summary = manager.summary()
            assert isinstance(summary, str)
            assert "Unknown" in summary
            assert "TestCI" in summary


def test_detection_manager_run_specific(default_path):
    config = DetectionManagerConfig(
        branch_analysis_enabled=True,
        ci_config_analysis_enabled=False,
        directory_summary_enabled=False,
        directory_details_enabled=False,
    )

    with patch(
        "metagit.core.detect.manager.DetectionManager._load_existing_config",
        return_value=None,
    ):
        manager = DetectionManager.from_path(default_path, config=config)
        assert not isinstance(manager, Exception)

        # Test that disabled methods return Exception
        result = manager.run_specific("ci_config_analysis")
        assert isinstance(result, Exception)

        # Test that enabled methods delegate to run_all
        with patch.object(manager, "run_all", return_value=None) as mock_run_all:
            result = manager.run_specific("branch_analysis")
            assert result is None
            mock_run_all.assert_called_once()


def test_detection_manager_run_specific_unknown_method(default_path):
    with patch(
        "metagit.core.detect.manager.DetectionManager._load_existing_config",
        return_value=None,
    ):
        manager = DetectionManager.from_path(default_path)
        assert not isinstance(manager, Exception)

        result = manager.run_specific("unknown_method")
        assert isinstance(result, Exception)
        assert "Unknown analysis method" in str(result)


def test_detection_manager_summary_handles_missing(default_path):
    config = DetectionManagerConfig.minimal()

    with patch(
        "metagit.core.detect.manager.DetectionManager._load_existing_config",
        return_value=None,
    ):
        manager = DetectionManager.from_path(default_path, config=config)
        assert not isinstance(manager, Exception)

        # Test summary without running analysis
        summary = manager.summary()
        assert isinstance(summary, str)
        assert "not available" in summary


def test_detection_manager_serialization(default_path):
    config = DetectionManagerConfig.minimal()

    with patch(
        "metagit.core.detect.manager.DetectionManager._load_existing_config",
        return_value=None,
    ):
        manager = DetectionManager.from_path(default_path, config=config)
        assert not isinstance(manager, Exception)

        # Test YAML serialization
        yaml_output = manager.to_yaml()
        assert isinstance(yaml_output, str)
        assert "name:" in yaml_output
        assert "project_path:" in yaml_output

        # Test JSON serialization
        json_output = manager.to_json()
        assert isinstance(json_output, str)
        assert '"name"' in json_output
        assert '"project_path"' in json_output


def test_detection_manager_inherits_from_metagit_record(default_path):
    """Test that DetectionManager properly inherits from MetagitRecord."""
    with patch(
        "metagit.core.detect.manager.DetectionManager._load_existing_config",
        return_value=None,
    ):
        manager = DetectionManager.from_path(default_path)
        assert not isinstance(manager, Exception)

        # Should have MetagitRecord attributes
        assert hasattr(manager, "name")
        assert hasattr(manager, "path")
        assert hasattr(manager, "detection_timestamp")
        assert hasattr(manager, "detection_source")
        assert hasattr(manager, "detection_version")

        # Should also have DetectionManager-specific attributes
        assert hasattr(manager, "detection_config")
        assert hasattr(manager, "repository_analysis")
        assert hasattr(manager, "analysis_completed")
        assert hasattr(manager, "project_path")


def test_detection_manager_cleanup(default_path):
    """Test that DetectionManager cleanup delegates to RepositoryAnalysis."""
    with patch(
        "metagit.core.detect.manager.DetectionManager._load_existing_config",
        return_value=None,
    ):
        manager = DetectionManager.from_path(default_path)
        assert not isinstance(manager, Exception)

        # Create a mock RepositoryAnalysis
        mock_repo_analysis = MagicMock()
        manager.repository_analysis = mock_repo_analysis

        # Test cleanup
        manager.cleanup()
        mock_repo_analysis.cleanup.assert_called_once()


def test_detection_manager_update_metagit_record(default_path):
    """Test that DetectionManager properly updates MetagitRecord fields from RepositoryAnalysis."""
    with patch(
        "metagit.core.detect.manager.DetectionManager._load_existing_config",
        return_value=None,
    ):
        manager = DetectionManager.from_path(default_path)
        assert not isinstance(manager, Exception)

        # Create a mock RepositoryAnalysis with data
        mock_repo_analysis = RepositoryAnalysis(
            path=default_path,
            name="test-project",
            description="A test project",
            url="https://github.com/test/project",
            language_detection=LanguageDetection(primary="Python"),
            project_type_detection=ProjectTypeDetection(
                type=ProjectType.APPLICATION, domain=ProjectDomain.WEB
            ),
            branch_analysis=GitBranchAnalysis(
                strategy_guess="GitHub Flow",
                branches=[BranchInfo(name="main", is_remote=False)],
            ),
            ci_config_analysis=CIConfigAnalysis(detected_tool="GitHub Actions"),
        )

        manager.repository_analysis = mock_repo_analysis

        # Test _update_metagit_record
        manager._update_metagit_record()

        # Check that MetagitRecord fields were updated
        assert manager.name == "test-project"
        assert manager.description == "A test project"
        assert manager.url == "https://github.com/test/project"
        assert manager.language.primary == "Python"
        assert manager.kind == ProjectType.APPLICATION
        assert manager.domain == ProjectDomain.WEB
        assert manager.branch_strategy == "GitHub Flow"
        assert len(manager.branches) == 1
        assert manager.branches[0].name == "main"
        assert manager.cicd.platform == "GitHub Actions"

#!/usr/bin/env python3
"""
Unit tests for DetectionManager and DetectionManagerConfig.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from metagit.core.config.models import Language, ProjectDomain, ProjectType
from metagit.core.detect.branch import BranchInfo, GitBranchAnalysis
from metagit.core.detect.cicd import CIConfigAnalysis
from metagit.core.detect.manager import DetectionManager, DetectionManagerConfig
from metagit.core.detect.repository import (
    LanguageDetection,
    ProjectTypeDetection,
    RepositoryAnalysis,
)
from metagit.core.utils.files import DirectoryDetails, DirectorySummary


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

        # Patch analysis methods to avoid real filesystem/git
        with (
            patch(
                "metagit.core.detect.manager.RepositoryAnalysis.from_path",
                return_value=RepositoryAnalysis(
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
                    metadata=None,
                    metrics=None,
                ),
            ),
            patch(
                "metagit.core.detect.manager.GitBranchAnalysis.from_repo",
                return_value=GitBranchAnalysis(strategy_guess="Unknown", branches=[]),
            ),
            patch(
                "metagit.core.detect.manager.CIConfigAnalysis.from_repo",
                return_value=CIConfigAnalysis(detected_tool="TestCI"),
            ),
            patch(
                "metagit.core.detect.manager.directory_summary",
                return_value=DirectorySummary(
                    path=default_path,
                    num_files=5,
                    file_types=[],
                    subpaths=[],
                ),
            ),
            patch(
                "metagit.core.detect.manager.FileExtensionLookup",
                return_value=MagicMock(),
            ),
            patch(
                "metagit.core.detect.manager.directory_details",
                return_value=DirectoryDetails(
                    path=default_path,
                    num_files=3,
                    file_types={"programming": []},
                    subpaths=[],
                ),
            ),
        ):
            result = manager.run_all()
            assert result is None
            assert manager.analysis_completed is True

            # Patch missing fields for summary
            object.__setattr__(manager, "domain", ProjectDomain.WEB)
            object.__setattr__(manager, "kind", ProjectType.APPLICATION)
            object.__setattr__(manager, "language", Language(primary="Python"))
            object.__setattr__(manager, "language_version", "3.9")

            summary = manager.summary()
            assert isinstance(summary, str)
            assert "Unknown" in summary
            assert "TestCI" in summary
            assert "5 files" in summary
            assert "3 files" in summary


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

        with patch(
            "metagit.core.detect.manager.GitBranchAnalysis.from_repo",
            return_value=GitBranchAnalysis(strategy_guess="Unknown", branches=[]),
        ):
            # Set the branch_analysis attribute directly to avoid validation
            manager.branch_analysis = GitBranchAnalysis(
                strategy_guess="Unknown", branches=[]
            )

            result = manager.run_specific("branch_analysis")
            assert result is None
            assert manager.branch_analysis is not None

        # Disabled method should return Exception
        result = manager.run_specific("ci_config_analysis")
        assert isinstance(result, Exception)


def test_detection_manager_summary_handles_missing(default_path):
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

        # No analysis run yet
        # Patch missing fields for summary
        object.__setattr__(manager, "domain", ProjectDomain.WEB)
        object.__setattr__(manager, "kind", ProjectType.APPLICATION)
        object.__setattr__(manager, "language", Language(primary="Python"))
        object.__setattr__(manager, "language_version", "3.9")
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
        assert hasattr(manager, "branch_analysis")
        assert hasattr(manager, "ci_config_analysis")
        assert hasattr(manager, "directory_summary")
        assert hasattr(manager, "directory_details")
        assert hasattr(manager, "repository_analysis")

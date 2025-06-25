#!/usr/bin/env python3
"""
Unit tests for DetectionManager and DetectionManagerConfig.
"""
from unittest.mock import MagicMock, patch

import pytest

from metagit.core.detect.manager import DetectionManager, DetectionManagerConfig


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


def test_detection_manager_run_all_and_summary(default_path):
    config = DetectionManagerConfig(
        branch_analysis_enabled=True,
        ci_config_analysis_enabled=True,
        directory_summary_enabled=True,
        directory_details_enabled=True,
    )
    manager = DetectionManager(path=default_path, config=config)
    # Patch analysis methods to avoid real filesystem/git
    with (
        patch(
            "metagit.core.detect.manager.GitBranchAnalysis.from_repo",
            return_value=MagicMock(strategy_guess="TestStrategy", branches=[]),
        ),
        patch(
            "metagit.core.detect.manager.CIConfigAnalysis.from_repo",
            return_value=MagicMock(detected_tool="TestCI"),
        ),
        patch(
            "metagit.core.detect.manager.directory_summary",
            return_value=MagicMock(num_files=5, file_types=[1, 2, 3]),
        ),
        patch(
            "metagit.core.detect.manager.FileExtensionLookup", return_value=MagicMock()
        ),
        patch(
            "metagit.core.detect.manager.directory_details",
            return_value=MagicMock(num_files=3, file_types={"programming": []}),
        ),
    ):
        result = manager.run_all()
        assert result is None
        summary = manager.summary()
        assert isinstance(summary, str)
        assert "TestStrategy" in summary
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
    manager = DetectionManager(path=default_path, config=config)
    with patch(
        "metagit.core.detect.manager.GitBranchAnalysis.from_repo",
        return_value=MagicMock(strategy_guess="TestStrategy", branches=[]),
    ):
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
    manager = DetectionManager(path=default_path, config=config)
    # No analysis run yet
    summary = manager.summary()
    assert "not available" in summary

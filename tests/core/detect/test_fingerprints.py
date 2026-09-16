#!/usr/bin/env python
"""Fingerprint marker mapping shared by detectors and org indexing."""

from metagit.core.detect.fingerprints import matching_paths, tags_for_paths


def test_tags_for_common_markers() -> None:
    paths = [
        "Dockerfile",
        "infra/main.tf",
        "src/App.csproj",
        ".github/workflows/ci.yml",
        "azure-pipelines.yml",
        "pyproject.toml",
    ]
    tags = tags_for_paths(paths)
    assert "docker" in tags
    assert "terraform" in tags
    assert "dotnet" in tags
    assert "github-actions" in tags
    assert "azure-pipelines" in tags
    assert "python" in tags


def test_has_matches_filename_and_tag() -> None:
    paths = ["deploy/azure-pipelines.yml", "Makefile"]
    assert matching_paths(paths, has="azure-pipelines.yml")
    assert matching_paths(paths, has="make")

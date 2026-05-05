#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.services.repo_ops
"""

from pathlib import Path

from git import Repo

from metagit.core.mcp.services.repo_ops import RepoOperationsService


def test_pull_requires_explicit_mutation_enable(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    Repo.init(repo_dir)
    service = RepoOperationsService()

    result = service.sync(repo_path=str(repo_dir), mode="pull", allow_mutation=False)

    assert result["ok"] is False
    assert "Mutation disabled" in str(result["error"])


def test_inspect_reports_repo_status(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    Repo.init(repo_dir)
    service = RepoOperationsService()

    result = service.inspect(repo_path=str(repo_dir))

    assert result["ok"] is True

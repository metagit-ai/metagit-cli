#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.services.workspace_sync
"""

from pathlib import Path
from unittest.mock import MagicMock

from git import Repo

from metagit.core.mcp.services.workspace_sync import WorkspaceSyncService


def test_sync_many_dry_run_skips_git_calls(tmp_path: Path) -> None:
    repo_path = tmp_path / "alpha" / "repo-one"
    repo_path.mkdir(parents=True)
    Repo.init(repo_path)
    rows = [
        {
            "project_name": "alpha",
            "repo_name": "repo-one",
            "repo_path": str(repo_path),
            "exists": True,
            "is_git_repo": True,
            "url": None,
        }
    ]
    repo_ops = MagicMock()
    service = WorkspaceSyncService(repo_ops=repo_ops)

    payload = service.sync_many(rows, dry_run=True)

    assert payload["summary"]["dry_run"] is True
    assert payload["results"][0]["dry_run"] is True
    repo_ops.sync.assert_not_called()


def test_sync_many_only_if_missing_skips_existing(tmp_path: Path) -> None:
    repo_path = tmp_path / "alpha" / "repo-one"
    repo_path.mkdir(parents=True)
    Repo.init(repo_path)
    rows = [
        {
            "project_name": "alpha",
            "repo_name": "repo-one",
            "repo_path": str(repo_path),
            "exists": True,
            "is_git_repo": True,
            "url": None,
        }
    ]
    repo_ops = MagicMock()
    service = WorkspaceSyncService(repo_ops=repo_ops)

    payload = service.sync_many(rows, only_if="missing", dry_run=False)

    assert payload["results"][0]["skipped"] is True
    assert payload["results"][0]["skipped_reason"] == "already_present"
    repo_ops.sync.assert_not_called()

#!/usr/bin/env python
"""
Unit tests for WorkspaceIndexService managed repo rows (tags, status).
"""

from pathlib import Path

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService


def test_build_index_synced_git_repo_with_tags_and_paths(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    repo_dir = workspace_root / "svc-auth"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    config = MetagitConfig(
        name="test",
        kind="application",
        workspace={
            "projects": [
                {
                    "name": "platform",
                    "repos": [
                        {
                            "name": "svc-auth",
                            "path": "./svc-auth",
                            "url": "https://example.com/org/svc-auth.git",
                            "sync": True,
                            "tags": {"tier": "1", "domain": "auth"},
                        }
                    ],
                }
            ]
        },
    )
    service = WorkspaceIndexService()
    rows = service.build_index(config=config, workspace_root=str(workspace_root))

    assert len(rows) == 1
    row = rows[0]
    assert row["project_name"] == "platform"
    assert row["repo_name"] == "svc-auth"
    assert row["configured_path"] == "./svc-auth"
    assert row["tags"] == {"tier": "1", "domain": "auth"}
    assert row["exists"] is True
    assert row["is_git_repo"] is True
    assert row["status"] == "synced"
    assert row["url"] == "https://example.com/org/svc-auth.git"
    assert row["sync"] is True


def test_build_index_url_only_repo_uses_project_mount_path(tmp_path: Path) -> None:
    workspace_root = tmp_path / ".metagit"
    workspace_root.mkdir()
    repo_dir = workspace_root / "platform" / "svc-auth"
    repo_dir.mkdir(parents=True)
    (repo_dir / ".git").mkdir()

    config = MetagitConfig(
        name="test",
        kind="application",
        workspace={
            "projects": [
                {
                    "name": "platform",
                    "repos": [
                        {
                            "name": "svc-auth",
                            "url": "https://example.com/org/svc-auth.git",
                            "sync": True,
                        }
                    ],
                }
            ]
        },
    )
    service = WorkspaceIndexService()
    rows = service.build_index(config=config, workspace_root=str(workspace_root))

    assert len(rows) == 1
    row = rows[0]
    assert row["configured_path"] is None
    assert row["repo_path"] == str(repo_dir.resolve())
    assert row["exists"] is True
    assert row["status"] == "synced"


def test_build_index_missing_path_is_configured_missing(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    config = MetagitConfig(
        name="test",
        kind="application",
        workspace={
            "projects": [
                {
                    "name": "default",
                    "repos": [
                        {
                            "name": "ghost-repo",
                            "path": "./not-on-disk",
                            "sync": False,
                        }
                    ],
                }
            ]
        },
    )
    service = WorkspaceIndexService()
    rows = service.build_index(config=config, workspace_root=str(workspace_root))

    assert len(rows) == 1
    row = rows[0]
    assert row["exists"] is False
    assert row["is_git_repo"] is False
    assert row["status"] == "configured_missing"

#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.services.workspace_index
"""

from pathlib import Path

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService


def test_workspace_index_resolves_repo_paths(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    repo_path = workspace_root / "repo-a"
    repo_path.mkdir()

    config = MetagitConfig(
        name="test",
        kind="application",
        workspace={
            "projects": [
                {
                    "name": "default",
                    "repos": [
                        {
                            "name": "repo-a",
                            "path": "./repo-a",
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
    assert rows[0]["repo_name"] == "repo-a"
    assert rows[0]["exists"] is True
    assert rows[0]["sync"] is True


def test_manifest_root_path_resolves_to_definition_root(tmp_path: Path) -> None:
    definition_root = tmp_path / "coordinator"
    definition_root.mkdir()
    sync_root = definition_root / ".metagit"
    sync_root.mkdir()
    git_dir = definition_root / ".git"
    git_dir.mkdir()

    config = MetagitConfig(
        name="umbrella",
        kind="umbrella",
        workspace={
            "projects": [
                {
                    "name": "default",
                    "repos": [
                        {
                            "name": "framework",
                            "path": "./",
                            "sync": False,
                        }
                    ],
                }
            ]
        },
    )
    rows = WorkspaceIndexService().build_index(
        config=config,
        workspace_root=str(sync_root),
        definition_root=str(definition_root),
    )

    assert len(rows) == 1
    assert rows[0]["repo_path"] == str(definition_root.resolve())
    assert rows[0]["is_git_repo"] is True
    assert rows[0]["status"] == "synced"

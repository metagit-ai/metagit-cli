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
                            "kind": "repository",
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

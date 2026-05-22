#!/usr/bin/env python
"""
Unit tests for metagit.core.context.workspace_map_service.WorkspaceMapService.
"""

from pathlib import Path

from git import Repo

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig
from metagit.core.context.workspace_map_service import WorkspaceMapService


def _write_single_project_workspace(tmp_path: Path, *, tag_repo: bool) -> Path:
    repo_dir = tmp_path / "svc" / "repo-one"
    repo_dir.mkdir(parents=True)
    Repo.init(repo_dir)

    repo_block = "\n".join(
        [
            "        - name: repo-one",
            "          path: svc/repo-one",
            "          sync: true",
            *(
                [
                    "          tags:",
                    "            team: backend",
                    "            tier: infra",
                ]
                if tag_repo
                else []
            ),
        ]
    )

    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: test-workspace-map",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: demo",
                "      description: Demo project bundle",
                "      repos:",
                repo_block,
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return tmp_path


def _load_config(workspace_root: Path) -> MetagitConfig:
    manager = MetagitConfigManager(config_path=workspace_root / ".metagit.yml")
    loaded = manager.load_config()
    assert not isinstance(loaded, Exception)
    return loaded


def test_build_maps_catalog_to_workspace_map_result(tmp_path: Path) -> None:
    workspace_root = _write_single_project_workspace(tmp_path, tag_repo=True)
    config = _load_config(workspace_root)
    config_path = str(workspace_root / ".metagit.yml")
    root = str(workspace_root)

    service = WorkspaceMapService()
    result = service.build(
        config=config,
        config_path=config_path,
        workspace_root=root,
    )

    assert result.tier == 0
    assert result.workspace_name == config.name == "test-workspace-map"
    assert result.workspace_root == str(workspace_root.resolve())
    assert result.config_path == str((workspace_root / ".metagit.yml").resolve())
    assert result.project_count == 1
    assert result.repo_count == 1
    assert result.active_project is None

    assert len(result.projects) == 1
    assert result.projects[0].name == "demo"
    assert result.projects[0].repo_count == 1
    assert result.projects[0].description == "Demo project bundle"

    assert len(result.repos) == 1
    entry = result.repos[0]
    resolved_repo = str((workspace_root / "svc" / "repo-one").resolve())
    assert entry.project_name == "demo"
    assert entry.repo_name == "repo-one"
    assert entry.repo_path == resolved_repo
    assert entry.exists is True
    assert entry.status == "synced"
    assert entry.tags == ["team=backend", "tier=infra"]


def test_build_passes_through_active_project(tmp_path: Path) -> None:
    workspace_root = _write_single_project_workspace(tmp_path, tag_repo=False)
    config = _load_config(workspace_root)
    config_path = str(workspace_root / ".metagit.yml")
    root = str(workspace_root)

    service = WorkspaceMapService()
    result = service.build(
        config=config,
        config_path=config_path,
        workspace_root=root,
        active_project="demo",
    )

    assert result.active_project == "demo"


def test_build_missing_repo_reports_configured_missing(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: empty-mount",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: demo",
                "      repos:",
                "        - name: nowhere",
                "          path: does-not-exist",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    config = _load_config(tmp_path)
    config_path = str(tmp_path / ".metagit.yml")
    root = str(tmp_path)

    service = WorkspaceMapService()
    result = service.build(
        config=config,
        config_path=config_path,
        workspace_root=root,
    )

    assert result.repo_count == 1
    assert len(result.repos) == 1
    assert result.repos[0].exists is False
    assert result.repos[0].status == "configured_missing"
    resolved = str((tmp_path / "does-not-exist").resolve())
    assert result.repos[0].repo_path == resolved
    assert result.repos[0].tags is None

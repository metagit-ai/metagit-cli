#!/usr/bin/env python
"""Tests for workspace layout rename and move service."""

from pathlib import Path

import yaml

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.workspace.layout_service import WorkspaceLayoutService


def _setup_workspace(tmp_path: Path) -> tuple[Path, str, str]:
    sync_root = tmp_path / "sync"
    sync_root.mkdir()
    (sync_root / "alpha").mkdir()
    (sync_root / "alpha" / "svc-a").mkdir()
    (sync_root / "alpha" / "svc-a" / "README.md").write_text("demo", encoding="utf-8")
    manifest = {
        "name": "test",
        "kind": "application",
        "workspace": {
            "projects": [
                {
                    "name": "alpha",
                    "repos": [{"name": "svc-a", "path": "alpha/svc-a", "sync": True}],
                },
                {"name": "beta", "repos": []},
            ]
        },
    }
    config_path = tmp_path / ".metagit.yml"
    config_path.write_text(yaml.dump(manifest), encoding="utf-8")
    manager = MetagitConfigManager(str(config_path))
    loaded = manager.load_config()
    assert not isinstance(loaded, Exception)
    return loaded, str(config_path), str(sync_root)


def test_rename_project_moves_sync_folder(tmp_path: Path) -> None:
    config, config_path, sync_root = _setup_workspace(tmp_path)
    service = WorkspaceLayoutService()
    result = service.rename_project(
        config,
        config_path,
        sync_root,
        from_name="alpha",
        to_name="apps",
    )
    assert result.ok
    assert (Path(sync_root) / "apps").is_dir()
    assert not (Path(sync_root) / "alpha").exists()
    manager = MetagitConfigManager(config_path)
    reloaded = manager.load_config()
    assert not isinstance(reloaded, Exception)
    assert any(project.name == "apps" for project in reloaded.workspace.projects)


def test_rename_repo_moves_mount(tmp_path: Path) -> None:
    config, config_path, sync_root = _setup_workspace(tmp_path)
    service = WorkspaceLayoutService()
    result = service.rename_repo(
        config,
        config_path,
        sync_root,
        project_name="alpha",
        from_name="svc-a",
        to_name="svc-b",
    )
    assert result.ok
    assert (Path(sync_root) / "alpha" / "svc-b").exists()
    assert not (Path(sync_root) / "alpha" / "svc-a").exists()


def test_move_repo_between_projects(tmp_path: Path) -> None:
    config, config_path, sync_root = _setup_workspace(tmp_path)
    service = WorkspaceLayoutService()
    result = service.move_repo(
        config,
        config_path,
        sync_root,
        repo_name="svc-a",
        from_project="alpha",
        to_project="beta",
    )
    assert result.ok
    assert (Path(sync_root) / "beta" / "svc-a").exists()
    assert not (Path(sync_root) / "alpha" / "svc-a").exists()
    manager = MetagitConfigManager(config_path)
    reloaded = manager.load_config()
    assert not isinstance(reloaded, Exception)
    beta = next(p for p in reloaded.workspace.projects if p.name == "beta")
    assert any(repo.name == "svc-a" for repo in beta.repos)


def test_dry_run_does_not_mutate(tmp_path: Path) -> None:
    config, config_path, sync_root = _setup_workspace(tmp_path)
    service = WorkspaceLayoutService()
    result = service.rename_project(
        config,
        config_path,
        sync_root,
        from_name="alpha",
        to_name="apps",
        dry_run=True,
    )
    assert result.ok
    assert (Path(sync_root) / "alpha").exists()
    assert (result.data or {}).get("manifest_updated") is False

#!/usr/bin/env python
"""Tests for workspace catalog list and mutation service."""

from pathlib import Path

import yaml

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.workspace.catalog_service import WorkspaceCatalogService


def _write_manifest(tmp_path: Path, projects: list[dict] | None = None) -> tuple[Path, str]:
    manifest = {
        "name": "test-workspace",
        "kind": "application",
        "workspace": {"projects": projects or []},
    }
    config_path = tmp_path / ".metagit.yml"
    config_path.write_text(yaml.dump(manifest), encoding="utf-8")
    manager = MetagitConfigManager(str(config_path))
    loaded = manager.load_config()
    assert not isinstance(loaded, Exception)
    return loaded, str(config_path)


def test_list_projects_and_repos(tmp_path: Path) -> None:
    config, config_path = _write_manifest(
        tmp_path,
        [
            {
                "name": "platform",
                "repos": [
                    {"name": "svc-a", "path": "platform/svc-a", "sync": True},
                ],
            }
        ],
    )
    service = WorkspaceCatalogService()
    projects = service.list_projects(config)
    assert projects.data["project_count"] == 1
    repos = service.list_repos(config, str(tmp_path), project_name="platform")
    assert repos.data["repo_count"] == 1
    workspace = service.list_workspace(config, config_path, str(tmp_path))
    assert workspace.data["summary"]["repo_count"] == 1


def test_add_and_remove_project(tmp_path: Path) -> None:
    config, config_path = _write_manifest(tmp_path)
    service = WorkspaceCatalogService()
    added = service.add_project(config, config_path, name="infra")
    assert added.ok
    manager = MetagitConfigManager(config_path)
    reloaded = manager.load_config()
    assert not isinstance(reloaded, Exception)
    assert any(project.name == "infra" for project in reloaded.workspace.projects)
    removed = service.remove_project(reloaded, config_path, name="infra")
    assert removed.ok


def test_add_and_remove_repo(tmp_path: Path) -> None:
    config, config_path = _write_manifest(
        tmp_path,
        [{"name": "platform", "repos": []}],
    )
    service = WorkspaceCatalogService()
    built = service.build_repo_from_fields(
        name="svc-b",
        path="platform/svc-b",
        sync=True,
    )
    assert not isinstance(built, Exception)
    from metagit.core.workspace.catalog_models import CatalogError

    assert not isinstance(built, CatalogError)
    added = service.add_repo(
        config,
        config_path,
        project_name="platform",
        repo=built,
    )
    assert added.ok
    manager = MetagitConfigManager(config_path)
    reloaded = manager.load_config()
    assert not isinstance(reloaded, Exception)
    removed = service.remove_repo(
        reloaded,
        config_path,
        project_name="platform",
        repo_name="svc-b",
    )
    assert removed.ok

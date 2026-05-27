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


def test_add_repo_rejects_duplicate_identity(tmp_path: Path) -> None:
    from metagit.core.project.models import ProjectPath
    from metagit.core.workspace.catalog_models import CatalogError

    config, config_path = _write_manifest(
        tmp_path,
        [
            {
                "name": "alpha",
                "repos": [
                    {
                        "name": "svc",
                        "url": "https://github.com/example/svc.git",
                    }
                ],
            },
            {"name": "beta", "repos": []},
        ],
    )
    service = WorkspaceCatalogService()
    built = service.build_repo_from_fields(
        name="svc-copy",
        url="https://github.com/example/svc.git",
    )
    assert not isinstance(built, CatalogError)
    result = service.add_repo(
        config,
        config_path,
        project_name="beta",
        repo=built,
    )
    assert not result.ok
    assert result.error is not None
    assert result.error.kind == "duplicate_identity"


def test_add_repo_ensure_noop_when_matching(tmp_path: Path) -> None:
    config, config_path = _write_manifest(
        tmp_path,
        [
            {
                "name": "platform",
                "repos": [
                    {
                        "name": "svc-b",
                        "url": "https://github.com/example/svc-b.git",
                    }
                ],
            }
        ],
    )
    service = WorkspaceCatalogService()
    built = service.build_repo_from_fields(
        name="svc-b",
        url="https://github.com/example/svc-b.git",
    )
    assert not isinstance(built, Exception)
    result = service.add_repo(
        config,
        config_path,
        project_name="platform",
        repo=built,
        ensure=True,
    )
    assert result.ok
    assert result.operation == "noop"


def test_add_repo_ensure_conflict_on_url_mismatch(tmp_path: Path) -> None:
    config, config_path = _write_manifest(
        tmp_path,
        [
            {
                "name": "platform",
                "repos": [
                    {
                        "name": "svc-b",
                        "url": "https://github.com/example/svc-b.git",
                    }
                ],
            }
        ],
    )
    service = WorkspaceCatalogService()
    built = service.build_repo_from_fields(
        name="svc-b",
        url="https://github.com/example/other.git",
    )
    assert not isinstance(built, Exception)
    result = service.add_repo(
        config,
        config_path,
        project_name="platform",
        repo=built,
        ensure=True,
    )
    assert not result.ok
    assert result.error is not None
    assert result.error.kind == "conflict"


def test_add_project_ensure_noop(tmp_path: Path) -> None:
    config, config_path = _write_manifest(
        tmp_path,
        [{"name": "infra", "repos": []}],
    )
    service = WorkspaceCatalogService()
    result = service.add_project(config, config_path, name="infra", ensure=True)
    assert result.ok
    assert result.operation == "noop"


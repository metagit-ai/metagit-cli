#!/usr/bin/env python
"""
Unit tests for ManagedRepoSearchService.
"""

from pathlib import Path

from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.project.search_service import ManagedRepoSearchService
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _config(tmp_path: Path) -> MetagitConfig:
    workspace_root = tmp_path / "workspace"
    app_repo = workspace_root / "platform" / "abacus-app"
    module_repo = workspace_root / "shared" / "abacus-module"
    app_repo.mkdir(parents=True)
    module_repo.mkdir(parents=True)
    (app_repo / ".git").mkdir()
    (module_repo / ".git").mkdir()
    return MetagitConfig(
        name="workspace",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="platform",
                    repos=[
                        ProjectPath(
                            name="abacus-app",
                            path="platform/abacus-app",
                            url="https://github.com/example/abacus-app.git",
                            sync=True,
                            tags={"code": "abacus", "domain": "terraform"},
                        )
                    ],
                ),
                WorkspaceProject(
                    name="shared",
                    repos=[
                        ProjectPath(
                            name="abacus-module",
                            path="shared/abacus-module",
                            url="https://github.com/example/abacus-module.git",
                            sync=True,
                            tags={"code": "abacus", "domain": "terraform-module"},
                        )
                    ],
                ),
            ]
        ),
    )


def test_search_prioritizes_exact_repo_name(tmp_path: Path) -> None:
    service = ManagedRepoSearchService()
    result = service.search(
        config=_config(tmp_path),
        workspace_root=str(tmp_path / "workspace"),
        query="abacus-app",
    )
    assert result.matches[0].repo_name == "abacus-app"
    assert "repo_name:exact" in result.matches[0].match_reasons


def test_search_can_filter_by_tag(tmp_path: Path) -> None:
    service = ManagedRepoSearchService()
    result = service.search(
        config=_config(tmp_path),
        workspace_root=str(tmp_path / "workspace"),
        query="abacus",
        tags={"domain": "terraform-module"},
    )
    assert [match.repo_name for match in result.matches] == ["abacus-module"]


def test_search_filters_by_status_and_has_url(tmp_path: Path) -> None:
    service = ManagedRepoSearchService()
    missing_repo = tmp_path / "workspace" / "platform" / "missing-app"
    missing_repo.mkdir(parents=True)
    config = _config(tmp_path)
    config.workspace.projects[0].repos.append(
        ProjectPath(
            name="missing-app",
            path="platform/missing-app",
            sync=True,
        )
    )
    result = service.search(
        config=config,
        workspace_root=str(tmp_path / "workspace"),
        query="*",
        status=["configured_missing"],
        has_url=False,
        sort="name",
    )
    assert [match.repo_name for match in result.matches] == ["missing-app"]


def test_search_sorts_by_project_name(tmp_path: Path) -> None:
    service = ManagedRepoSearchService()
    result = service.search(
        config=_config(tmp_path),
        workspace_root=str(tmp_path / "workspace"),
        query="abacus",
        sort="project",
    )
    project_names = [match.project_name for match in result.matches]
    assert project_names == sorted(project_names)


def test_resolve_one_returns_ambiguous_match(tmp_path: Path) -> None:
    service = ManagedRepoSearchService()
    resolved = service.resolve_one(
        config=_config(tmp_path),
        workspace_root=str(tmp_path / "workspace"),
        query="abacus",
        synced_only=True,
    )
    assert resolved.error is not None
    assert resolved.error.kind == "ambiguous_match"

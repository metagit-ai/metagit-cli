#!/usr/bin/env python
"""Tests for workspace project protection in catalog mutations."""

from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.catalog_service import WorkspaceCatalogService
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _protected_config() -> MetagitConfig:
  return MetagitConfig(
    name="ws",
    workspace=Workspace(
      projects=[
        WorkspaceProject(
          name="platform",
          protected=True,
          repos=[
            ProjectPath(name="api", url="https://github.com/example/api.git"),
          ],
        )
      ]
    ),
  )


def test_remove_protected_project_requires_force(tmp_path) -> None:
  config_path = tmp_path / ".metagit.yml"
  config = _protected_config()
  service = WorkspaceCatalogService()
  result = service.remove_project(config, str(config_path), name="platform")
  assert result.ok is False
  assert result.error is not None
  assert result.error.kind == "protected"


def test_add_repo_to_protected_project_requires_force(tmp_path) -> None:
  config_path = tmp_path / ".metagit.yml"
  config = _protected_config()
  service = WorkspaceCatalogService()
  repo = ProjectPath(name="new", url="https://github.com/example/new.git")
  result = service.add_repo(
    config,
    str(config_path),
    project_name="platform",
    repo=repo,
  )
  assert result.ok is False
  assert result.error is not None
  assert result.error.kind == "protected"

#!/usr/bin/env python
"""Tests for DerivedProjectService."""

from __future__ import annotations

from pathlib import Path

from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.derived_project_service import DerivedProjectService
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _base_config() -> MetagitConfig:
  return MetagitConfig(
    name="umbrella",
    workspace=Workspace(
      projects=[
        WorkspaceProject(
          name="portfolio",
          repos=[
            ProjectPath(
              name="api",
              url="https://github.com/example/api.git",
              tags={"tier": "1", "lang": "py"},
            ),
            ProjectPath(
              name="web",
              url="https://github.com/example/web.git",
              tags={"tier": "2"},
            ),
          ],
        ),
        WorkspaceProject(
          name="local",
          repos=[
            ProjectPath(
              name="notes",
              path="/tmp/notes",
              tags={"kind": "scratch"},
            ),
          ],
        ),
      ]
    ),
  )


def test_create_refresh_include_exclude(tmp_path: Path) -> None:
  config_path = str(tmp_path / ".metagit.yml")
  config = _base_config()
  service = DerivedProjectService()

  created = service.create(
    config,
    config_path,
    name="surgical",
    selections=["portfolio/api", "local/notes"],
    description="Agent working set",
  )
  assert created.ok is True
  assert created.operation == "create"
  assert set(created.repo_names) == {"api", "notes"}

  project = next(p for p in config.workspace.projects if p.name == "surgical")
  assert project.derived is not None
  assert project.derived.enabled is True
  assert project.dedupe is not None
  assert project.dedupe.enabled is True
  api = next(r for r in project.repos if r.name == "api")
  assert api.derived_from is not None
  assert api.derived_from.project == "portfolio"
  assert api.tags["tier"] == "1"

  # Mutate source identity then refresh
  source_api = next(r for r in config.workspace.projects[0].repos if r.name == "api")
  source_api.url = "https://github.com/example/api-v2.git"
  source_api.tags = {"tier": "1", "lang": "python"}
  api.tags["local_only"] = "keep"

  refreshed = service.refresh(config, config_path, project_name="surgical", repo_names=["api"])
  assert refreshed.ok is True
  api = next(r for r in project.repos if r.name == "api")
  assert str(api.url) == "https://github.com/example/api-v2.git"
  assert api.tags["lang"] == "python"
  assert api.tags["local_only"] == "keep"
  assert api.derived_from is not None
  assert api.derived_from.refreshed_at is not None

  # Membership frozen: source gaining a repo does not auto-include
  assert len(project.repos) == 2
  included = service.include(
    config,
    config_path,
    project_name="surgical",
    selection="portfolio/web",
  )
  assert included.ok is True
  assert included.operation == "include"
  assert len(project.repos) == 3

  excluded = service.exclude(config, config_path, project_name="surgical", repo_name="notes")
  assert excluded.ok is True
  assert {r.name for r in project.repos} == {"api", "web"}


def test_refresh_errors_when_source_missing(tmp_path: Path) -> None:
  config_path = str(tmp_path / ".metagit.yml")
  config = _base_config()
  service = DerivedProjectService()
  created = service.create(
    config,
    config_path,
    name="surgical",
    selections=["portfolio/api"],
  )
  assert created.ok is True
  config.workspace.projects[0].repos = [
    r for r in config.workspace.projects[0].repos if r.name != "api"
  ]
  result = service.refresh(config, config_path, project_name="surgical")
  assert result.ok is False
  assert result.error is not None
  assert result.error.kind == "source_not_found"


def test_create_rejects_duplicate_identity_without_dedupe(tmp_path: Path) -> None:
  config_path = str(tmp_path / ".metagit.yml")
  config = _base_config()
  service = DerivedProjectService()
  result = service.create(
    config,
    config_path,
    name="surgical",
    selections=["portfolio/api"],
    enable_dedupe=False,
  )
  assert result.ok is False
  assert result.error is not None
  assert result.error.kind == "duplicate_identity"

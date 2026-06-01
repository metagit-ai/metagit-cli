#!/usr/bin/env python
"""Tests for WorkspaceProject schema extensions."""

from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


def test_workspace_project_accepts_tags_documentation_metadata() -> None:
  project = WorkspaceProject(
    name="platform",
    description="Shared infra",
    protected=True,
    tags={"class": "infrastructure"},
    documentation=["docs/platform.md"],
    metadata={"owner": "platform-team"},
    repos=[],
  )
  assert project.protected is True
  assert project.tags["class"] == "infrastructure"
  assert project.documentation is not None
  assert len(project.documentation) == 1
  assert project.metadata["owner"] == "platform-team"


def test_project_path_rejects_kind_field() -> None:
  try:
    ProjectPath.model_validate({"name": "svc", "kind": "service", "url": "https://x.git"})
    raised = False
  except Exception:
    raised = True
  assert raised is True


def test_manifest_loads_without_repo_kind() -> None:
  config = MetagitConfig(
    name="ws",
    workspace=Workspace(
      projects=[
        WorkspaceProject(
          name="portfolio",
          tags={"team": "core"},
          repos=[
            ProjectPath(
              name="api",
              url="https://github.com/example/api.git",
              tags={"tier": "1"},
            )
          ],
        )
      ]
    ),
  )
  assert config.workspace is not None
  assert config.workspace.projects[0].tags["team"] == "core"

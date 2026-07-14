#!/usr/bin/env python
"""Tests for WorkspaceProject schema extensions."""

from metagit.core.config.models import MetagitConfig
from metagit.core.config import models
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


def test_dependency_accepts_kind_field() -> None:
  dep = models.Dependency(
    name="python",
    kind=models.DependencyKind.DOCKER_IMAGE,
    ref="./Dockerfile",
    url="https://hub.docker.com/_/python",
  )
  assert dep.kind == models.DependencyKind.DOCKER_IMAGE


def test_manifest_dependencies_reject_kind_on_project_path_only() -> None:
  config = MetagitConfig.model_validate(
    {
      "name": "demo",
      "dependencies": [
        {
          "name": "python",
          "kind": "docker_image",
          "ref": "./Dockerfile",
        }
      ],
    }
  )
  assert config.dependencies is not None
  assert config.dependencies[0].kind == "docker_image"


def test_derived_project_requires_provenance_on_repos() -> None:
  try:
    WorkspaceProject(
      name="surgical",
      derived={"enabled": True, "sources": [{"project": "portfolio"}]},
      repos=[ProjectPath(name="api", url="https://github.com/example/api.git")],
    )
    raised = False
  except Exception:
    raised = True
  assert raised is True


def test_derived_project_accepts_provenance() -> None:
  project = WorkspaceProject(
    name="surgical",
    derived={
      "enabled": True,
      "sources": [{"project": "portfolio", "repos": ["api"]}],
    },
    repos=[
      ProjectPath(
        name="api",
        url="https://github.com/example/api.git",
        derived_from={"project": "portfolio", "repo": "api"},
      )
    ],
  )
  assert project.derived is not None
  assert project.derived.enabled is True
  assert project.repos[0].derived_from is not None
  assert project.repos[0].derived_from.project == "portfolio"

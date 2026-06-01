#!/usr/bin/env python
"""Tests for inherited project tags in workspace index and search."""

from metagit.core.config.models import MetagitConfig
from metagit.core.mcp.services.workspace_index import WorkspaceIndexService
from metagit.core.project.models import ProjectPath
from metagit.core.project.search_service import ManagedRepoSearchService
from metagit.core.workspace.models import Workspace, WorkspaceProject


def _config_with_project_tags() -> MetagitConfig:
  return MetagitConfig(
    name="ws",
    workspace=Workspace(
      projects=[
        WorkspaceProject(
          name="portfolio",
          tags={"class": "application", "shared": "yes"},
          repos=[
            ProjectPath(
              name="api",
              url="https://github.com/example/api.git",
              tags={"tier": "1", "shared": "repo"},
            )
          ],
        )
      ]
    ),
  )


def test_index_merges_project_and_repo_tags() -> None:
  rows = WorkspaceIndexService().build_index(
    config=_config_with_project_tags(),
    workspace_root="/tmp/ws",
  )
  assert len(rows) == 1
  row = rows[0]
  assert row["project_tags"] == {"class": "application", "shared": "yes"}
  assert row["repo_tags"] == {"tier": "1", "shared": "repo"}
  assert row["tags"] == {
    "class": "application",
    "shared": "repo",
    "tier": "1",
  }


def test_search_tag_filter_matches_inherited_project_tag() -> None:
  result = ManagedRepoSearchService().search(
    config=_config_with_project_tags(),
    workspace_root="/tmp/ws",
    query="*",
    tags={"class": "application"},
    limit=5,
  )
  assert len(result.matches) == 1
  assert result.matches[0].tags["class"] == "application"

#!/usr/bin/env python
"""
Unit tests for ProjectManager.select_repo behavior.
"""

from pathlib import Path
from typing import Optional

from metagit.core.config.models import MetagitConfig
from metagit.core.project.manager import ProjectManager
from metagit.core.project.models import ProjectKind, ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


class _DummyLogger:
  def set_level(self, _: str) -> None:
    return

  def warning(self, _: str) -> None:
    return

  def debug(self, _: str) -> None:
    return


def _build_metagit_config() -> MetagitConfig:
  return MetagitConfig(
    name="test-config",
    workspace=Workspace(
      projects=[
        WorkspaceProject(
          name="proj-one",
          repos=[
            ProjectPath(
              name="repo-a",
              description="Core repository",
              kind=ProjectKind.APPLICATION,
              path="/tmp/repo-a",
              url="https://example.com/repo-a.git",
              language="python",
              language_version="3.12",
              package_manager="uv",
              frameworks=["textual", "pydantic"],
              source_provider="github",
              source_namespace="org-a",
              protected=True,
              ref="services/repo-a",
            ),
            ProjectPath(name="missing-repo", description="Configured but missing"),
          ],
        )
      ]
    ),
  )


def test_select_repo_respects_gitignore_and_sets_total_count(tmp_path, monkeypatch) -> None:
  workspace_root = tmp_path / "workspace"
  project_root = workspace_root / "proj-one"
  project_root.mkdir(parents=True)
  (project_root / ".gitignore").write_text("ignored-repo\n", encoding="utf-8")
  (project_root / "repo-a").mkdir()
  (project_root / "ignored-repo").mkdir()

  captured = {}

  class _DummyFinder:
    def __init__(self, config) -> None:
      captured["config"] = config

    def run(self) -> Optional[ProjectPath]:
      return None

  monkeypatch.setattr("metagit.core.project.manager.FuzzyFinder", _DummyFinder)

  manager = ProjectManager(workspace_root, _DummyLogger())
  _ = manager.select_repo(_build_metagit_config(), "proj-one", show_preview=True)

  finder_config = captured["config"]
  item_names = [item.name for item in finder_config.items]
  assert "ignored-repo" not in item_names
  assert "repo-a" in item_names
  assert "missing-repo" in item_names
  assert finder_config.total_count == 2


def test_select_repo_preview_contains_extended_metadata(tmp_path, monkeypatch) -> None:
  workspace_root = tmp_path / "workspace"
  project_root = workspace_root / "proj-one"
  project_root.mkdir(parents=True)
  (project_root / "repo-a").mkdir()

  captured = {}

  class _DummyFinder:
    def __init__(self, config) -> None:
      captured["config"] = config

    def run(self) -> Optional[ProjectPath]:
      return None

  monkeypatch.setattr("metagit.core.project.manager.FuzzyFinder", _DummyFinder)

  manager = ProjectManager(workspace_root, _DummyLogger())
  _ = manager.select_repo(_build_metagit_config(), "proj-one", show_preview=True)

  target_item = next(
    item for item in captured["config"].items if item.name == "repo-a"
  )
  preview = target_item.description
  assert "Status: ✅ Managed" in preview
  assert "Path: /tmp/repo-a" in preview
  assert "URL: https://example.com/repo-a.git" in preview
  assert "Language: python" in preview
  assert "Language Version: 3.12" in preview
  assert "Package Manager: uv" in preview
  assert "Frameworks: textual, pydantic" in preview
  assert "Source Provider: github" in preview
  assert "Source Namespace: org-a" in preview
  assert "Protected: True" in preview

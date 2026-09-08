#!/usr/bin/env python
"""
Unit tests for ProjectManager.select_repo behavior.
"""

from pathlib import Path
from typing import Optional

from metagit.core.config.models import MetagitConfig
from metagit.core.project.manager import ProjectManager
from metagit.core.project.models import ProjectPath
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
  assert "URL: https://example.com/repo-a.git" in preview
  assert "Language: python" in preview
  assert "Language Version: 3.12" in preview
  assert "Package Manager: uv" in preview
  assert "Frameworks: textual, pydantic" in preview
  assert "Source Provider: github" in preview
  assert "Source Namespace: org-a" in preview
  assert "Protected: True" in preview


def test_select_repo_missing_project_returns_value_error(tmp_path) -> None:
  manager = ProjectManager(tmp_path / "workspace", _DummyLogger())
  result = manager.select_repo(_build_metagit_config(), "missing-project")
  assert isinstance(result, ValueError)
  assert "missing-project" in str(result)
  assert "proj-one" in str(result)


def test_resolve_selected_repo_path_returns_sync_mount(tmp_path) -> None:
  workspace_root = tmp_path / "workspace"
  project_root = workspace_root / "proj-one"
  repo_dir = project_root / "repo-a"
  repo_dir.mkdir(parents=True)

  config = MetagitConfig(
    name="test-config",
    workspace=Workspace(
      projects=[
        WorkspaceProject(
          name="proj-one",
          repos=[
            ProjectPath(
              name="repo-a",
              url="https://example.com/repo-a.git",
            ),
          ],
        )
      ]
    ),
  )

  manager = ProjectManager(workspace_root, _DummyLogger())
  resolved = manager.resolve_selected_repo_path(
    config,
    "proj-one",
    "repo-a",
    definition_root=str(tmp_path),
  )
  assert resolved == str(repo_dir.resolve())


def test_select_workspace_repos_flattens_managed_labels(tmp_path, monkeypatch) -> None:
  workspace_root = tmp_path / "workspace"
  (workspace_root / "platform" / "backend").mkdir(parents=True)
  (workspace_root / "edge" / "gateway").mkdir(parents=True)
  (workspace_root / "platform" / "stray").mkdir()

  config = MetagitConfig(
    name="test-config",
    workspace=Workspace(
      projects=[
        WorkspaceProject(
          name="platform",
          repos=[ProjectPath(name="backend", url="https://example.com/backend.git")],
        ),
        WorkspaceProject(
          name="edge",
          repos=[ProjectPath(name="gateway", url="https://example.com/gateway.git")],
        ),
      ]
    ),
  )
  captured = {}

  class _DummyFinder:
    def __init__(self, finder_config) -> None:
      captured["config"] = finder_config

    def run(self) -> None:
      return None

  monkeypatch.setattr("metagit.core.project.manager.FuzzyFinder", _DummyFinder)
  manager = ProjectManager(workspace_root, _DummyLogger())
  _ = manager.select_workspace_repos(config, show_preview=True)

  names = [item.name for item in captured["config"].items]
  assert set(names) == {"platform/backend", "edge/gateway"}
  assert "platform/stray" not in names
  backend = next(item for item in captured["config"].items if item.name == "platform/backend")
  assert "Status: ✅ Managed" in backend.description
  assert "URL: https://example.com/backend.git" in backend.description
  assert captured["config"].enable_preview is True
  assert captured["config"].preview_field == "description"


def test_select_workspace_repos_include_unmanaged(tmp_path, monkeypatch) -> None:
  workspace_root = tmp_path / "workspace"
  (workspace_root / "platform" / "backend").mkdir(parents=True)
  (workspace_root / "platform" / "stray").mkdir()

  config = MetagitConfig(
    name="test-config",
    workspace=Workspace(
      projects=[
        WorkspaceProject(
          name="platform",
          repos=[ProjectPath(name="backend")],
        ),
      ]
    ),
  )
  captured = {}

  class _DummyFinder:
    def __init__(self, finder_config) -> None:
      captured["config"] = finder_config

    def run(self):
      stray = next(item for item in captured["config"].items if item.name == "platform/stray")
      return stray

  monkeypatch.setattr("metagit.core.project.manager.FuzzyFinder", _DummyFinder)
  manager = ProjectManager(workspace_root, _DummyLogger())
  selected = manager.select_workspace_repos(config, include_unmanaged=True)
  names = [item.name for item in captured["config"].items]
  assert "platform/backend" in names
  assert "platform/stray" in names
  stray = next(item for item in captured["config"].items if item.name == "platform/stray")
  assert stray.opacity == 0.5
  assert "Status: ❌ Unmanaged" in stray.description
  assert Path(selected).resolve() == (workspace_root / "platform" / "stray").resolve()


def test_select_workspace_repos_empty_returns_value_error(tmp_path) -> None:
  manager = ProjectManager(tmp_path / "workspace", _DummyLogger())
  result = manager.select_workspace_repos(
    MetagitConfig(name="empty", workspace=Workspace(projects=[])),
  )
  assert isinstance(result, ValueError)


def test_resolve_selected_repo_path_unknown_repo_returns_value_error(tmp_path) -> None:
  workspace_root = tmp_path / "workspace"
  (workspace_root / "proj-one").mkdir(parents=True)

  manager = ProjectManager(workspace_root, _DummyLogger())
  result = manager.resolve_selected_repo_path(
    _build_metagit_config(),
    "proj-one",
    "nope-repo",
    definition_root=str(tmp_path),
  )
  assert isinstance(result, ValueError)
  assert "nope-repo" in str(result)

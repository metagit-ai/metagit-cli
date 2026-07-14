#!/usr/bin/env python
"""Tests for in-TUI project → repository navigation."""

from __future__ import annotations

from pathlib import Path

import pytest

from metagit.core.tui.app import (
  MessageScreen,
  MetagitTuiApp,
  ProjectSelectScreen,
  RepoSelectScreen,
)
from metagit.core.tui.navigation import (
  ProjectRepoSelection,
  list_manifest_projects,
  list_manifest_repos,
  maybe_single_project,
  open_selected_repo,
)


def _write_umbrella(tmp_path: Path) -> tuple[Path, Path, Path]:
  workspace = tmp_path / ".metagit"
  (workspace / "platform" / "backend").mkdir(parents=True)
  (workspace / "platform" / "frontend").mkdir(parents=True)
  (workspace / "data" / "warehouse").mkdir(parents=True)

  manifest = tmp_path / ".metagit.yml"
  manifest.write_text(
    "\n".join(
      [
        "name: umbrella",
        "kind: umbrella",
        "workspace:",
        "  projects:",
        "    - name: platform",
        "      repos:",
        "        - name: backend",
        "          url: https://example.com/backend.git",
        "        - name: frontend",
        "          url: https://example.com/frontend.git",
        "    - name: data",
        "      repos:",
        "        - name: warehouse",
        "          url: https://example.com/warehouse.git",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  app_cfg = tmp_path / "metagit.config.yaml"
  app_cfg.write_text(
    "\n".join(
      [
        "config:",
        "  description: test",
        "  editor: echo",
        "  workspace:",
        f"    path: {workspace.as_posix()}",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  return manifest, app_cfg, workspace


def test_list_manifest_projects_and_repos(tmp_path: Path) -> None:
  manifest, _, _ = _write_umbrella(tmp_path)
  projects = list_manifest_projects(str(manifest))
  assert projects == ["platform", "data"]
  repos = list_manifest_repos(str(manifest), "platform")
  assert repos == ["backend", "frontend"]


def test_maybe_single_project() -> None:
  assert maybe_single_project(["only"]) == "only"
  assert maybe_single_project(["a", "b"]) is None
  assert maybe_single_project([]) is None


def test_open_selected_repo_opens_editor(tmp_path: Path, monkeypatch) -> None:
  manifest, app_cfg, workspace = _write_umbrella(tmp_path)
  opened: list[str] = []

  def _fake_open(editor: str, path: str):
    opened.append(path)
    return None

  monkeypatch.setattr("metagit.core.tui.navigation.open_editor", _fake_open)
  result = open_selected_repo(
    app_config_path=str(app_cfg),
    manifest_path=str(manifest),
    project_name="platform",
    repo_name="backend",
  )
  assert not isinstance(result, Exception)
  expected = str((workspace / "platform" / "backend").resolve())
  assert result.path == expected
  assert opened == [expected]


@pytest.mark.asyncio
async def test_home_quit_via_q_is_clean(tmp_path: Path) -> None:
  manifest, app_cfg, _ = _write_umbrella(tmp_path)
  app = MetagitTuiApp(
    app_config_path=str(app_cfg),
    manifest_path=str(manifest),
    cwd=str(tmp_path),
  )
  async with app.run_test() as pilot:
    await pilot.press("q")
  assert app.return_value is None


@pytest.mark.asyncio
async def test_home_opens_project_then_repo_screens(tmp_path: Path, monkeypatch) -> None:
  manifest, app_cfg, workspace = _write_umbrella(tmp_path)

  def _fake_open(**kwargs):
    return ProjectRepoSelection(
      project=kwargs["project_name"],
      repo=kwargs["repo_name"],
      path=str(workspace / kwargs["project_name"] / kwargs["repo_name"]),
    )

  monkeypatch.setattr("metagit.core.tui.app.open_selected_repo", _fake_open)
  app = MetagitTuiApp(
    app_config_path=str(app_cfg),
    manifest_path=str(manifest),
    cwd=str(tmp_path),
  )
  async with app.run_test() as pilot:
    # Home defaults to first item: Select project → repository
    await pilot.press("enter")
    assert isinstance(app.screen, ProjectSelectScreen)
    await pilot.press("enter")  # platform
    assert isinstance(app.screen, RepoSelectScreen)
    await pilot.press("enter")  # backend
    assert isinstance(app.screen, MessageScreen)
    assert app.screen._title == "Opened repository"


@pytest.mark.asyncio
async def test_single_project_skips_to_repos(tmp_path: Path) -> None:
  workspace = tmp_path / ".metagit"
  (workspace / "solo" / "api").mkdir(parents=True)
  manifest = tmp_path / ".metagit.yml"
  manifest.write_text(
    "\n".join(
      [
        "name: solo-app",
        "kind: application",
        "workspace:",
        "  projects:",
        "    - name: solo",
        "      repos:",
        "        - name: api",
        "          url: https://example.com/api.git",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  app_cfg = tmp_path / "metagit.config.yaml"
  app_cfg.write_text(
    "\n".join(
      [
        "config:",
        "  description: test",
        "  editor: echo",
        "  workspace:",
        f"    path: {workspace.as_posix()}",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  app = MetagitTuiApp(
    app_config_path=str(app_cfg),
    manifest_path=str(manifest),
    cwd=str(tmp_path),
  )
  async with app.run_test() as pilot:
    await pilot.press("enter")  # Select project → repository
    # on_mount auto-pushes RepoSelectScreen for sole project
    await pilot.pause()
    assert isinstance(app.screen, RepoSelectScreen)
    assert app.screen._project_name == "solo"

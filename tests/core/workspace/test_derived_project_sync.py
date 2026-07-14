#!/usr/bin/env python
"""Integration: derived project mounts share canonical clones via dedupe."""

from __future__ import annotations

import os
from pathlib import Path

from metagit.core.appconfig.models import WorkspaceDedupeConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.project.manager import ProjectManager
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.derived_project_service import DerivedProjectService
from metagit.core.workspace.models import Workspace, WorkspaceProject


class _DummyLogger:
  def set_level(self, _: str) -> None:
    return

  def warning(self, _: str) -> None:
    return

  def debug(self, _: str) -> None:
    return


def test_derived_project_sync_shares_canonical_clone(
  tmp_path: Path,
  monkeypatch,
) -> None:
  workspace_root = tmp_path / ".metagit"
  config_path = str(tmp_path / ".metagit.yml")
  url = "https://github.com/example/shared.git"

  def _fake_clone(clone_url: str, target: str, progress=None) -> None:  # noqa: ARG001
    os.makedirs(target, exist_ok=True)
    Path(target, ".git").mkdir(exist_ok=True)

  monkeypatch.setattr(
    "metagit.core.project.manager.git.Repo.clone_from",
    _fake_clone,
  )

  config = MetagitConfig(
    name="umbrella",
    workspace=Workspace(
      projects=[
        WorkspaceProject(
          name="portfolio",
          repos=[ProjectPath(name="shared", url=url)],
        )
      ]
    ),
  )
  created = DerivedProjectService().create(
    config,
    config_path,
    name="surgical",
    selections=["portfolio/shared"],
    enable_dedupe=True,
  )
  assert created.ok is True

  dedupe = WorkspaceDedupeConfig(enabled=True, canonical_dir="_canonical")
  manager = ProjectManager(workspace_root, _DummyLogger(), dedupe=dedupe)
  source = next(p for p in config.workspace.projects if p.name == "portfolio")
  derived = next(p for p in config.workspace.projects if p.name == "surgical")
  assert manager.sync(source) is True
  assert manager.sync(derived) is True

  mount_source = workspace_root / "portfolio" / "shared"
  mount_derived = workspace_root / "surgical" / "shared"
  assert mount_source.is_symlink()
  assert mount_derived.is_symlink()
  assert mount_source.resolve() == mount_derived.resolve()

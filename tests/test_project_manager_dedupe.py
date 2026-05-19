#!/usr/bin/env python
"""Integration tests for workspace dedupe sync layout."""

import os
from pathlib import Path

from metagit.core.appconfig.models import WorkspaceDedupeConfig
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


def test_deduped_local_path_creates_single_canonical_and_two_mounts(
  tmp_path: Path,
) -> None:
  source = tmp_path / "user-site"
  source.mkdir()
  (source / "index.html").write_text("hello", encoding="utf-8")

  workspace_root = tmp_path / ".metagit"
  dedupe = WorkspaceDedupeConfig(enabled=True, canonical_dir="_canonical")
  manager = ProjectManager(workspace_root, _DummyLogger(), dedupe=dedupe)

  repo = ProjectPath(name="site", path=str(source), sync=True, kind=ProjectKind.WEBSITE)
  project_a = WorkspaceProject(name="local", repos=[repo])
  project_b = WorkspaceProject(
    name="mirror",
    repos=[
      ProjectPath(
        name="site",
        path=str(source),
        sync=True,
        kind=ProjectKind.WEBSITE,
      )
    ],
  )

  assert manager.sync(project_a) is True
  assert manager.sync(project_b) is True

  mount_a = workspace_root / "local" / "site"
  mount_b = workspace_root / "mirror" / "site"
  canonical = workspace_root / "_canonical"
  canonical_dirs = [path for path in canonical.iterdir() if path.is_dir() or path.is_symlink()]
  assert len(canonical_dirs) == 1
  assert mount_a.is_symlink()
  assert mount_b.is_symlink()
  assert mount_a.resolve() == canonical_dirs[0].resolve()
  assert mount_b.resolve() == canonical_dirs[0].resolve()
  assert (mount_a / "index.html").read_text(encoding="utf-8") == "hello"


def test_deduped_remote_clone_is_shared(
  tmp_path: Path,
  monkeypatch,
) -> None:
  workspace_root = tmp_path / ".metagit"
  dedupe = WorkspaceDedupeConfig(enabled=True, canonical_dir="_canonical")

  def _fake_clone(url: str, target: str, progress=None) -> None:  # noqa: ARG001
    os.makedirs(target, exist_ok=True)
    Path(target, ".git").mkdir(exist_ok=True)

  monkeypatch.setattr(
    "metagit.core.project.manager.git.Repo.clone_from",
    _fake_clone,
  )

  manager = ProjectManager(workspace_root, _DummyLogger(), dedupe=dedupe)
  url = "https://github.com/example/remote.git"
  project_a = WorkspaceProject(
    name="p1",
    repos=[ProjectPath(name="remote", url=url, kind=ProjectKind.REPOSITORY)],
  )
  project_b = WorkspaceProject(
    name="p2",
    repos=[ProjectPath(name="remote", url=url, kind=ProjectKind.REPOSITORY)],
  )

  assert manager.sync(project_a) is True
  assert manager.sync(project_b) is True

  mount_a = workspace_root / "p1" / "remote"
  mount_b = workspace_root / "p2" / "remote"
  assert mount_a.is_symlink()
  assert mount_b.is_symlink()
  assert mount_a.resolve() == mount_b.resolve()

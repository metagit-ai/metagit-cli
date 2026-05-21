#!/usr/bin/env python
"""Tests for symlink mount hydration."""

import os
from pathlib import Path

from metagit.core.appconfig.models import WorkspaceDedupeConfig
from metagit.core.project.manager import ProjectManager
from metagit.core.project.models import ProjectKind, ProjectPath
from metagit.core.workspace.hydrate import collect_file_copy_jobs, materialize_symlink_mount
from metagit.core.workspace.models import WorkspaceProject


class _DummyLogger:
  def set_level(self, _: str) -> None:
    return

  def warning(self, _: str) -> None:
    return

  def debug(self, _: str) -> None:
    return


def test_collect_file_copy_jobs_counts_nested_files(tmp_path: Path) -> None:
  root = tmp_path / "src"
  (root / "a").mkdir(parents=True)
  (root / "a" / "one.txt").write_text("1", encoding="utf-8")
  (root / "b" / "two.txt").parent.mkdir(parents=True, exist_ok=True)
  (root / "b" / "two.txt").write_text("2", encoding="utf-8")
  jobs = collect_file_copy_jobs(root)
  assert len(jobs) == 2


def test_materialize_symlink_mount_replaces_link_with_directory(tmp_path: Path) -> None:
  source = tmp_path / "canonical"
  source.mkdir()
  (source / "README.md").write_text("hi", encoding="utf-8")
  mount = tmp_path / "project" / "repo"
  mount.parent.mkdir(parents=True)
  os.symlink(source, mount, target_is_directory=True)

  changed, error = materialize_symlink_mount(mount, repo_label="repo")
  assert error is None
  assert changed is True
  assert mount.is_dir()
  assert not mount.is_symlink()
  assert (mount / "README.md").read_text(encoding="utf-8") == "hi"
  assert source.exists()


def test_project_sync_hydrate_after_deduped_symlink(tmp_path: Path) -> None:
  source = tmp_path / "user-site"
  source.mkdir()
  (source / "index.html").write_text("hello", encoding="utf-8")

  workspace_root = tmp_path / ".metagit"
  dedupe = WorkspaceDedupeConfig(enabled=True, canonical_dir="_canonical")
  manager = ProjectManager(workspace_root, _DummyLogger(), dedupe=dedupe)
  repo = ProjectPath(name="site", path=str(source), sync=True, kind=ProjectKind.WEBSITE)
  project = WorkspaceProject(name="local", repos=[repo])

  assert manager.sync(project) is True
  mount = workspace_root / "local" / "site"
  assert mount.is_symlink()

  assert manager.hydrate_project(project) is True
  assert mount.is_dir()
  assert not mount.is_symlink()
  assert (mount / "index.html").read_text(encoding="utf-8") == "hello"

#!/usr/bin/env python
"""Tests for workspace repository deduplication helpers."""

import os
from pathlib import Path

from metagit.core.appconfig.models import WorkspaceDedupeConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.project.models import ProjectKind, ProjectPath
from metagit.core.workspace import workspace_dedupe
from metagit.core.workspace.models import Workspace, WorkspaceProject


def test_build_repo_identity_same_url_different_projects() -> None:
  url = "https://github.com/example/org-repo.git"
  left = ProjectPath(name="a", url=url)
  right = ProjectPath(name="b", url=url + "/")
  assert workspace_dedupe.build_repo_identity(left) == workspace_dedupe.build_repo_identity(
    right
  )


def test_build_repo_identity_branch_suffix_differs() -> None:
  base = ProjectPath(name="svc", url="https://github.com/example/svc.git")
  branched = ProjectPath(
    name="svc",
    url="https://github.com/example/svc.git",
    branches=["main", "release"],
  )
  assert (
    workspace_dedupe.build_repo_identity(base).repo_key
    != workspace_dedupe.build_repo_identity(branched).repo_key
  )


def test_find_duplicate_identities_reports_existing() -> None:
  shared = ProjectPath(
    name="shared",
    kind=ProjectKind.REPOSITORY,
    url="https://github.com/example/shared.git",
  )
  config = MetagitConfig(
    name="cfg",
    workspace=Workspace(
      projects=[
        WorkspaceProject(name="alpha", repos=[shared]),
        WorkspaceProject(name="beta", repos=[]),
      ]
    ),
  )
  incoming = ProjectPath(
    name="shared-copy",
    url="https://github.com/example/shared.git",
  )
  matches = workspace_dedupe.find_duplicate_identities(config, incoming)
  assert matches == [("alpha", "shared")]


def test_ensure_symlink_creates_and_repairs(tmp_path: Path) -> None:
  target = tmp_path / "canonical"
  target.mkdir()
  mount = tmp_path / "project" / "repo"
  changed, error = workspace_dedupe.ensure_symlink(mount, target)
  assert error is None
  assert changed is True
  assert mount.is_symlink()
  assert mount.resolve() == target.resolve()

  broken = tmp_path / "broken-link"
  if broken.exists() or broken.is_symlink():
    broken.unlink()
  os.symlink("missing-target", broken)
  changed_repair, repair_error = workspace_dedupe.ensure_symlink(broken, target)
  assert repair_error is None
  assert changed_repair is True
  assert broken.resolve() == target.resolve()


def test_list_orphan_canonical_dirs(tmp_path: Path) -> None:
  dedupe = WorkspaceDedupeConfig(enabled=True, canonical_dir="_canonical")
  workspace_root = tmp_path / ".metagit"
  canonical_root = workspace_root / "_canonical"
  (canonical_root / "used-key").mkdir(parents=True)
  (canonical_root / "orphan-key").mkdir(parents=True)
  references = {"used-key": [("alpha", "repo")]}
  orphans = workspace_dedupe.list_orphan_canonical_dirs(
    workspace_root,
    dedupe,
    references,
  )
  assert [path.name for path in orphans] == ["orphan-key"]

#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.services.workspace_snapshot
"""

import json
from pathlib import Path

from git import Repo

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.mcp.services.project_context import ProjectContextService
from metagit.core.mcp.services.session_store import SessionStore
from metagit.core.mcp.services.workspace_snapshot import WorkspaceSnapshotService


def _write_workspace(tmp_path: Path) -> str:
  repo_path = tmp_path / "alpha" / "repo-one"
  repo_path.mkdir(parents=True)
  Repo.init(repo_path)
  (tmp_path / ".metagit.yml").write_text(
    "\n".join(
      [
        "name: workspace",
        "kind: application",
        "workspace:",
        "  projects:",
        "    - name: alpha",
        "      repos:",
        "        - name: repo-one",
        "          path: alpha/repo-one",
        "          sync: true",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  return str(tmp_path)


def _load_config(tmp_path: Path):
  manager = MetagitConfigManager(config_path=tmp_path / ".metagit.yml")
  loaded = manager.load_config()
  assert not isinstance(loaded, Exception)
  return loaded


def test_create_writes_snapshot_file(tmp_path: Path) -> None:
  root = _write_workspace(tmp_path)
  config = _load_config(tmp_path)
  service = WorkspaceSnapshotService()

  payload = service.create(
    config=config,
    workspace_root=root,
    label="before-switch",
  )

  snapshot_path = tmp_path / ".metagit" / "snapshots" / f"{payload['snapshot_id']}.json"
  assert snapshot_path.is_file()
  raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
  assert raw["label"] == "before-switch"
  assert len(raw["repos"]) == 1


def test_restore_missing_snapshot_returns_error(tmp_path: Path) -> None:
  root = _write_workspace(tmp_path)
  config = _load_config(tmp_path)
  service = WorkspaceSnapshotService()

  result = service.restore(
    config=config,
    workspace_root=root,
    snapshot_id="missing-id",
  )

  assert result.ok is False
  assert result.error == "snapshot_not_found"


def test_restore_switches_active_project(tmp_path: Path) -> None:
  root = _write_workspace(tmp_path)
  config = _load_config(tmp_path)
  context = ProjectContextService()
  context.switch(config=config, workspace_root=root, project_name="alpha")
  snapshot_service = WorkspaceSnapshotService()
  created = snapshot_service.create(config=config, workspace_root=root)

  store = SessionStore(workspace_root=root)
  store.set_active_project(project_name="")
  cleared = store.get_workspace_meta()
  cleared.active_project = None
  store.save_workspace_meta(meta=cleared)

  restored = snapshot_service.restore(
    config=config,
    workspace_root=root,
    snapshot_id=created["snapshot_id"],
    switch_project=True,
  )

  assert restored.ok is True
  assert restored.context is not None
  assert restored.context.project_name == "alpha"
  meta = store.get_workspace_meta()
  assert meta.active_project == "alpha"

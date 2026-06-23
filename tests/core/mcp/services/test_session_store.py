#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.services.session_store
"""

import json
from pathlib import Path

import pytest

from metagit.core.mcp.services.session_store import SessionStore
from metagit.core.workspace.context_models import WorkspaceSessionMeta


def test_get_workspace_meta_returns_defaults_when_missing(tmp_path: Path) -> None:
  store = SessionStore(workspace_root=str(tmp_path))
  meta = store.get_workspace_meta()
  assert meta.active_project is None


def test_set_active_project_persists_workspace_meta(tmp_path: Path) -> None:
  store = SessionStore(workspace_root=str(tmp_path))
  meta = store.set_active_project(project_name="alpha")
  assert meta.active_project == "alpha"
  reloaded = store.get_workspace_meta()
  assert reloaded.active_project == "alpha"
  assert reloaded.last_switch_at is not None


def test_project_session_roundtrip(tmp_path: Path) -> None:
  store = SessionStore(workspace_root=str(tmp_path))
  session = store.update_project_session(
    project_name="alpha",
    recent_repos=["/tmp/repo-a"],
    agent_notes="working on auth",
  )
  reloaded = store.get_project_session(project_name="alpha")
  assert reloaded.recent_repos == session.recent_repos
  assert reloaded.agent_notes == "working on auth"


def test_corrupt_project_session_returns_empty(tmp_path: Path) -> None:
  store = SessionStore(workspace_root=str(tmp_path))
  store.ensure_dirs()
  path = store.sessions_dir / "alpha.json"
  path.write_text("{not-json", encoding="utf-8")
  session = store.get_project_session(project_name="alpha")
  assert session.project_name == "alpha"
  assert session.recent_repos == []


def test_env_override_secret_value_rejected(tmp_path: Path) -> None:
  store = SessionStore(workspace_root=str(tmp_path))
  with pytest.raises(ValueError):
    store.update_project_session(
      project_name="alpha",
      env_overrides={"METAGIT_TOKEN": "Bearer secret"},
    )


def test_save_workspace_meta_writes_json(tmp_path: Path) -> None:
  store = SessionStore(workspace_root=str(tmp_path))
  store.save_workspace_meta(meta=WorkspaceSessionMeta(active_project="beta"))
  raw = json.loads((store.sessions_dir / "_workspace.json").read_text(encoding="utf-8"))
  assert raw["active_project"] == "beta"


def test_session_store_uses_custom_relative_session_path(tmp_path: Path) -> None:
  store = SessionStore(
    workspace_root=str(tmp_path),
    session_path="state/sessions",
  )
  store.save_workspace_meta(meta=WorkspaceSessionMeta(active_project="gamma"))
  assert store.sessions_dir == (tmp_path / "state" / "sessions").resolve()


def test_session_store_uses_env_session_path_override(
  tmp_path: Path,
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  monkeypatch.setenv("METAGIT_WORKSPACE_SESSION_PATH", "custom/sessions")
  store = SessionStore(workspace_root=str(tmp_path))
  store.save_workspace_meta(meta=WorkspaceSessionMeta(active_project="delta"))
  assert store.sessions_dir == (tmp_path / "custom" / "sessions").resolve()

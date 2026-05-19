#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.services.project_context
"""

from pathlib import Path

from git import Repo

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.config.models import MetagitConfig, Variable, VariableKind
from metagit.core.mcp.services.project_context import ProjectContextService
from metagit.core.mcp.services.session_store import SessionStore


def _write_multi_project_workspace(tmp_path: Path) -> str:
  alpha_repo = tmp_path / "alpha" / "repo-one"
  alpha_repo.mkdir(parents=True)
  Repo.init(alpha_repo)
  beta_repo = tmp_path / "beta" / "repo-two"
  beta_repo.mkdir(parents=True)
  Repo.init(beta_repo)
  (tmp_path / ".metagit.yml").write_text(
    "\n".join(
      [
        "name: workspace",
        "kind: application",
        "variables:",
        "  - name: METAGIT_APP_ENV",
        "    kind: string",
        "    ref: development",
        "workspace:",
        "  projects:",
        "    - name: alpha",
        "      agent_instructions: Focus on alpha services",
        "      repos:",
        "        - name: repo-one",
        "          path: alpha/repo-one",
        "          sync: true",
        "    - name: beta",
        "      repos:",
        "        - name: repo-two",
        "          path: beta/repo-two",
        "          sync: true",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  return str(tmp_path)


def _load_config(tmp_path: Path) -> MetagitConfig:
  manager = MetagitConfigManager(config_path=tmp_path / ".metagit.yml")
  loaded = manager.load_config()
  assert not isinstance(loaded, Exception)
  return loaded


def test_switch_sets_active_project_and_returns_repos(tmp_path: Path) -> None:
  root = _write_multi_project_workspace(tmp_path)
  config = _load_config(tmp_path)
  service = ProjectContextService()

  bundle = service.switch(
    config=config,
    workspace_root=root,
    project_name="alpha",
  )

  assert bundle.ok is True
  assert bundle.project_name == "alpha"
  assert bundle.agent_instructions == "Focus on alpha services"
  assert any(layer.layer == "project" for layer in bundle.instruction_layers)
  assert "Focus on alpha services" in bundle.effective_agent_instructions
  assert len(bundle.repos) == 1
  assert bundle.repos[0].repo_name == "repo-one"
  assert bundle.repos[0].branch is not None
  meta = SessionStore(workspace_root=root).get_workspace_meta()
  assert meta.active_project == "alpha"


def test_switch_unknown_project_returns_error(tmp_path: Path) -> None:
  root = _write_multi_project_workspace(tmp_path)
  config = _load_config(tmp_path)
  service = ProjectContextService()

  bundle = service.switch(
    config=config,
    workspace_root=root,
    project_name="missing",
  )

  assert bundle.ok is False
  assert bundle.error == "project_not_found"


def test_env_export_includes_metagit_and_config_variables(tmp_path: Path) -> None:
  root = _write_multi_project_workspace(tmp_path)
  config = _load_config(tmp_path)
  service = ProjectContextService()

  bundle = service.switch(
    config=config,
    workspace_root=root,
    project_name="alpha",
    restore_session=False,
  )

  assert bundle.env.export["METAGIT_PROJECT"] == "alpha"
  assert bundle.env.export["METAGIT_APP_ENV"] == "development"


def test_update_session_persists_notes(tmp_path: Path) -> None:
  root = _write_multi_project_workspace(tmp_path)
  config = _load_config(tmp_path)
  service = ProjectContextService()

  result = service.update_session(
    config=config,
    workspace_root=root,
    project_name="alpha",
    agent_notes="paused auth work",
  )

  assert result["ok"] is True
  session = SessionStore(workspace_root=root).get_project_session(project_name="alpha")
  assert session.agent_notes == "paused auth work"


def test_env_export_skips_sensitive_variable_ref(tmp_path: Path) -> None:
  config = MetagitConfig(
    name="workspace",
    kind="application",
    variables=[
      Variable(name="METAGIT_API_TOKEN", kind=VariableKind.STRING, ref="Bearer abc"),
    ],
    workspace={"projects": [{"name": "alpha", "repos": []}]},
  )
  service = ProjectContextService()
  bundle = service.switch(
    config=config,
    workspace_root=str(tmp_path),
    project_name="alpha",
    restore_session=False,
  )
  assert "METAGIT_API_TOKEN" not in bundle.env.export
  assert any("METAGIT_API_TOKEN" in hint for hint in bundle.env.hints)

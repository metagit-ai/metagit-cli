#!/usr/bin/env python
"""Unit tests for ContextSwitchService."""

from __future__ import annotations

from pathlib import Path

from metagit.core.config.manager import MetagitConfigManager
from metagit.core.context.context_switch_service import (
  ContextSwitchService,
  format_shell_exports,
)


def _write_workspace(tmp_path: Path) -> tuple[str, str, str]:
  sync = tmp_path / "sync"
  (sync / "attune" / "attune").mkdir(parents=True)
  manifest = tmp_path / ".metagit.yml"
  manifest.write_text(
    "\n".join(
      [
        "name: ws",
        "kind: umbrella",
        "workspace:",
        "  projects:",
        "    - name: attune",
        "      tags:",
        "        hermes_profile: attune",
        "      repos:",
        "        - name: attune",
        "          url: https://example.com/attune.git",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  return str(manifest), str(sync), str(tmp_path)


def test_switch_unknown_project(tmp_path: Path) -> None:
  manifest, sync, session = _write_workspace(tmp_path)
  config = MetagitConfigManager(manifest).load_config()
  assert not isinstance(config, Exception)
  result = ContextSwitchService().switch(
    config=config,
    config_path=manifest,
    workspace_root=sync,
    session_root=session,
    definition_root=session,
    project_name="missing",
    include_pack=False,
    include_prompt=False,
    include_objective=False,
  )
  assert result.ok is False
  assert result.error == "project_not_found"


def test_switch_unknown_repo(tmp_path: Path) -> None:
  manifest, sync, session = _write_workspace(tmp_path)
  config = MetagitConfigManager(manifest).load_config()
  assert not isinstance(config, Exception)
  result = ContextSwitchService().switch(
    config=config,
    config_path=manifest,
    workspace_root=sync,
    session_root=session,
    definition_root=session,
    project_name="attune",
    repo_name="missing",
    include_pack=False,
    include_prompt=False,
    include_objective=False,
  )
  assert result.ok is False
  assert result.error == "repo_not_found"


def test_switch_exports_agent_mode_and_hermes_tag(tmp_path: Path) -> None:
  manifest, sync, session = _write_workspace(tmp_path)
  config = MetagitConfigManager(manifest).load_config()
  assert not isinstance(config, Exception)
  result = ContextSwitchService().switch(
    config=config,
    config_path=manifest,
    workspace_root=sync,
    session_root=session,
    definition_root=session,
    project_name="attune",
    include_pack=False,
    include_prompt=False,
    include_objective=False,
  )
  assert result.ok is True
  assert result.env.get("METAGIT_AGENT_MODE") == "true"
  assert result.env.get("METAGIT_PROJECT") == "attune"
  assert result.env.get("METAGIT_HERMES_PROFILE") == "attune"


def test_switch_creates_objective(tmp_path: Path) -> None:
  manifest, sync, session = _write_workspace(tmp_path)
  config = MetagitConfigManager(manifest).load_config()
  assert not isinstance(config, Exception)
  result = ContextSwitchService().switch(
    config=config,
    config_path=manifest,
    workspace_root=sync,
    session_root=session,
    definition_root=session,
    project_name="attune",
    repo_name="attune",
    include_pack=False,
    include_prompt=False,
    include_objective=True,
  )
  assert result.ok is True
  assert result.objective_id is not None
  assert result.objective_id.startswith("ctx-")


def test_format_shell_exports_quotes_paths() -> None:
  text = format_shell_exports({"METAGIT_WORKING_DIR": "/tmp/has space"})
  assert "export METAGIT_WORKING_DIR=" in text
  assert "'/tmp/has space'" in text or '"/tmp/has space"' in text

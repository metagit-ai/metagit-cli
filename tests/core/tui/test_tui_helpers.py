#!/usr/bin/env python
"""Tests for Metagit TUI helpers."""

from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli
from metagit.core.tui.catalog import build_command_catalog
from metagit.core.tui.runner import MetagitCommandRunner
from metagit.core.tui.wizard import ConfigWizardService


def test_runner_build_argv_project_uses_short_manifest_flag() -> None:
  runner = MetagitCommandRunner(
    cwd="/tmp",
    app_config_path="/tmp/metagit.config.yaml",
    manifest_path="/tmp/.metagit.yml",
  )
  argv = runner.build_argv(["project", "sync"], manifest_option="-c", manifest_placement="after_group")
  assert argv[1:6] == [
    "--config",
    "/tmp/metagit.config.yaml",
    "project",
    "-c",
    "/tmp/.metagit.yml",
  ]
  assert argv[6:] == ["sync"]


def test_runner_build_argv_workspace_uses_long_manifest_flag() -> None:
  runner = MetagitCommandRunner(
    cwd="/tmp",
    app_config_path="/tmp/metagit.config.yaml",
    manifest_path="/tmp/.metagit.yml",
  )
  argv = runner.build_argv(
    ["workspace", "list", "--json"],
    manifest_option="--config",
    manifest_placement="after_group",
  )
  assert argv[1:7] == [
    "--config",
    "/tmp/metagit.config.yaml",
    "workspace",
    "--config",
    "/tmp/.metagit.yml",
    "list",
  ]
  assert argv[7:] == ["--json"]


def test_runner_build_argv_without_manifest() -> None:
  runner = MetagitCommandRunner(
    cwd="/tmp",
    app_config_path="/tmp/metagit.config.yaml",
  )
  argv = runner.build_argv(["appconfig", "show"])
  assert argv[1:] == ["--config", "/tmp/metagit.config.yaml", "appconfig", "show"]


def test_runner_run_action_search_appends_definition_after_query(monkeypatch) -> None:
  captured: dict[str, list[str]] = {}

  def _fake_run(argv, **_kwargs):
    captured["argv"] = argv

    class _Result:
      returncode = 0
      stdout = ""
      stderr = ""

    return _Result()

  monkeypatch.setattr("metagit.core.tui.runner.subprocess.run", _fake_run)

  runner = MetagitCommandRunner(
    cwd="/tmp",
    app_config_path="/tmp/metagit.config.yaml",
    manifest_path="/tmp/.metagit.yml",
  )
  action = next(item for section in build_command_catalog() for item in section.actions if item.id == "search")
  runner.run_action(action, extra_args=["backend"])
  argv = captured["argv"]
  assert argv[-2:] == ["--definition", "/tmp/.metagit.yml"]
  assert "backend" in argv


def test_config_wizard_apply_writes_app_config(tmp_path: Path) -> None:
  app_cfg = tmp_path / "metagit.config.yaml"
  service = ConfigWizardService(app_config_path=str(app_cfg))
  answers = service.default_answers()
  answers.editor = "vim"
  answers.workspace_path = str(tmp_path / "sync")
  result = service.apply(answers)
  assert not isinstance(result, Exception)
  assert app_cfg.is_file()
  reloaded = service.load_existing()
  assert reloaded.editor == "vim"
  assert reloaded.workspace.path == str(tmp_path / "sync")


def test_tui_rejects_agent_mode(tmp_path: Path) -> None:
  app_cfg = tmp_path / "metagit.config.yaml"
  app_cfg.write_text(
    "\n".join(
      [
        "config:",
        "  description: test",
        "  agent_mode: true",
      ]
    )
    + "\n",
    encoding="utf-8",
  )
  runner = CliRunner()
  result = runner.invoke(cli, ["--config", str(app_cfg), "tui"])
  assert result.exit_code != 0
  assert "agent mode" in result.output.lower()

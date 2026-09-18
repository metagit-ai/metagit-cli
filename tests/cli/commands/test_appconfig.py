#!/usr/bin/env python
"""CLI tests for appconfig bootstrap when no local metagit.config.yaml is present."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from metagit import DEFAULT_CONFIG
from metagit.cli.main import cli


def _empty_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
  home = tmp_path / "home"
  home.mkdir()
  monkeypatch.setattr(Path, "home", lambda: home)
  monkeypatch.setenv("HOME", str(home))
  monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
  return home


def test_appconfig_info_missing_local_does_not_use_workspace_folder(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
  _empty_home(tmp_path, monkeypatch)
  runner = CliRunner()
  with runner.isolated_filesystem():
    result = runner.invoke(cli, ["appconfig", "info"])
    assert result.exit_code == 0, result.output
    assert "./.metagit" not in result.output
    assert DEFAULT_CONFIG in result.output


def test_appconfig_validate_succeeds_without_local_file(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
  _empty_home(tmp_path, monkeypatch)
  runner = CliRunner()
  with runner.isolated_filesystem():
    result = runner.invoke(cli, ["appconfig", "validate"])
    assert result.exit_code == 0, result.output
    assert "Configuration is valid!" in result.output
    assert "./.metagit" not in result.output


def test_appconfig_info_uses_user_config_when_local_missing(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
  home = _empty_home(tmp_path, monkeypatch)
  user_cfg = home / ".config" / "metagit" / "config.yml"
  user_cfg.parent.mkdir(parents=True)
  user_cfg.write_text(
    "config:\n  description: user-level\n  editor: vim\n  workspace:\n    path: ~/.metagit\n",
    encoding="utf-8",
  )
  runner = CliRunner()
  with runner.isolated_filesystem():
    info = runner.invoke(cli, ["appconfig", "info"])
    assert info.exit_code == 0, info.output
    compact = "".join(info.output.split())
    assert "".join(str(user_cfg).split()) in compact
    assert "./.metagit" not in info.output
    show = runner.invoke(cli, ["appconfig", "show", "--format", "json"])
    assert show.exit_code == 0, show.output
    assert "user-level" in show.output
    assert "~/.metagit" in show.output

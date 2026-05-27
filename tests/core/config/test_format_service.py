#!/usr/bin/env python
"""Tests for config format service and fmt CLI."""

from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from metagit import DEFAULT_CONFIG
from metagit.cli.main import cli
from metagit.core.config.format_service import ConfigFormatService
from metagit.core.config.manager import MetagitConfigManager


def _minimal_metagit_yaml() -> str:
    return """\
description: 'Repositories for managing AWS accounts, including account creation,
  management, and shared resources. Each repository

  corresponds to a specific AWS account

  '
name: demo
workspace:
  projects:
  - description: secondary project
    name: default
    repos:
    - description: billing repo
      name: billing
      url: https://github.com/example/billing.git
"""


def test_render_metagit_normalizes_messy_description(tmp_path: Path) -> None:
    config_path = tmp_path / ".metagit.yml"
    config_path.write_text(_minimal_metagit_yaml(), encoding="utf-8")
    manager = MetagitConfigManager(config_path=str(config_path))
    loaded = manager.load_config()
    assert not isinstance(loaded, Exception)

    rendered = ConfigFormatService().render_metagit(loaded)
    assert "name: demo" in rendered
    assert rendered.index("name: demo") < rendered.index("description:")
    assert "description: |" in rendered or "description: 'Repositories" not in rendered
    assert "corresponds to a specific AWS account" in rendered
    assert "\n\n\n" not in rendered

    repo_section = rendered.split("repos:", maxsplit=1)[1]
    assert repo_section.index("name: billing") < repo_section.index("description:")


def test_format_metagit_writes_ordered_file(tmp_path: Path) -> None:
    config_path = tmp_path / ".metagit.yml"
    config_path.write_text(_minimal_metagit_yaml(), encoding="utf-8")

    result = ConfigFormatService().format_metagit(config_path)
    assert not isinstance(result, Exception)
    assert result.changed is True

    config_path.write_text(result.formatted, encoding="utf-8")
    roundtrip = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert roundtrip["name"] == "demo"
    assert roundtrip["workspace"]["projects"][0]["repos"][0]["name"] == "billing"


def test_fmt_check_reports_changes(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / ".metagit.yml"
    config_path.write_text(_minimal_metagit_yaml(), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "fmt", "--check", "--target", "metagit"],
    )
    assert result.exit_code == 1


def test_fmt_writes_in_place(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / ".metagit.yml"
    config_path.write_text(_minimal_metagit_yaml(), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "fmt", "--target", "metagit"],
    )
    assert result.exit_code == 0, result.output
    updated = config_path.read_text(encoding="utf-8")
    assert updated.index("name: demo") < updated.index("description:")

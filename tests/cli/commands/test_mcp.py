#!/usr/bin/env python
"""
CLI tests for metagit mcp commands.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def test_mcp_serve_accepts_root_option(tmp_path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli, ["mcp", "serve", "--root", str(tmp_path), "--status-once"]
    )

    assert result.exit_code == 0
    assert "mcp_state=" in result.output


def test_mcp_install_project_target_updates_config() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            ["mcp", "install", "--scope", "project", "--target", "opencode"],
        )

        assert result.exit_code == 0
        config_data = json.loads(Path(".opencode/mcp.json").read_text(encoding="utf-8"))
        assert "mcpServers" in config_data
        assert "metagit" in config_data["mcpServers"]


def test_mcp_install_github_copilot_uses_vscode_servers_key() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            ["mcp", "install", "--scope", "project", "--target", "github_copilot"],
        )

        assert result.exit_code == 0
        config_data = json.loads(Path(".vscode/mcp.json").read_text(encoding="utf-8"))
        assert "servers" in config_data
        assert "metagit" in config_data["servers"]
        entry = config_data["servers"]["metagit"]
        assert entry["args"] == ["mcp", "serve"]
        assert entry["command"] != "uvx"


def test_mcp_install_hermes_writes_yaml_under_hermes_home(tmp_path, monkeypatch) -> None:
    hermes_home = tmp_path / "hermes-home"
    hermes_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["mcp", "install", "--scope", "user", "--target", "hermes"],
    )
    assert result.exit_code == 0
    config_path = hermes_home / "config.yaml"
    assert config_path.exists()
    text = config_path.read_text(encoding="utf-8")
    assert "mcp_servers:" in text
    assert "metagit:" in text
    assert "uvx" not in text

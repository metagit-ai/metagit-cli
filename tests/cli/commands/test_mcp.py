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

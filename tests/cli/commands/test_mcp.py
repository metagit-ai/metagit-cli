#!/usr/bin/env python
"""
CLI tests for metagit mcp commands.
"""

from click.testing import CliRunner

from metagit.cli.main import cli


def test_mcp_serve_accepts_root_option(tmp_path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli, ["mcp", "serve", "--root", str(tmp_path), "--status-once"]
    )

    assert result.exit_code == 0
    assert "mcp_state=" in result.output

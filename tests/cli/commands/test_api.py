#!/usr/bin/env python
"""
CLI tests for metagit api commands.
"""

from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def test_api_cli_status_once_reports_bound_port(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["api", "serve", "--root", str(tmp_path), "--status-once", "--port", "0"],
    )
    assert result.exit_code == 0
    assert "api_state=ready" in result.output

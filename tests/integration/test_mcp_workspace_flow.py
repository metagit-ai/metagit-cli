#!/usr/bin/env python
"""
Integration tests for MCP workspace activation flow.
"""

from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def test_end_to_end_workspace_activation_and_discovery(tmp_path: Path) -> None:
    runner = CliRunner()
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    inactive_result = runner.invoke(
        cli,
        ["mcp", "serve", "--root", str(workspace_root), "--status-once"],
    )
    assert inactive_result.exit_code == 0
    assert "mcp_state=inactive_missing_config" in inactive_result.output

    (workspace_root / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: e2e-workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: default",
                "      repos: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    active_result = runner.invoke(
        cli,
        ["mcp", "serve", "--root", str(workspace_root), "--status-once"],
    )
    assert active_result.exit_code == 0
    assert "mcp_state=active" in active_result.output

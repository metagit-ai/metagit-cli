#!/usr/bin/env python
"""CLI tests for metagit workspace grep."""

import os
from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def _env_workspace_root(root: Path) -> dict[str, str]:
    workspace = str(root.resolve())
    return {**os.environ, "METAGIT_WORKSPACE_PATH": workspace}


def _write_grep_fixture(root: Path) -> None:
    (root / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: platform",
                "      repos:",
                "        - name: svc-a",
                "          path: platform/svc-a",
                "          sync: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    repo_dir = root / "platform" / "svc-a"
    repo_dir.mkdir(parents=True)
    (repo_dir / "main.py").write_text("grep-cli-marker = True\n", encoding="utf-8")


def test_workspace_grep_json_smoke() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp:
        root = Path(tmp)
        _write_grep_fixture(root)
        result = runner.invoke(
            cli,
            ["workspace", "grep", "grep-cli-marker", "--json"],
            env=_env_workspace_root(root),
            catch_exceptions=False,
        )
    assert result.exit_code == 0
    assert '"project_name": "platform"' in result.output
    assert '"repo_name": "svc-a"' in result.output
    assert "grep-cli-marker" in result.output


def test_workspace_grep_human_output() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp:
        root = Path(tmp)
        _write_grep_fixture(root)
        result = runner.invoke(
            cli,
            ["workspace", "grep", "grep-cli-marker"],
            env=_env_workspace_root(root),
            catch_exceptions=False,
        )
    assert result.exit_code == 0
    assert "platform/svc-a:" in result.output
    assert "grep-cli-marker" in result.output

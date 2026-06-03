#!/usr/bin/env python
"""CLI tests for metagit workspace grep."""

import os
from pathlib import Path
from unittest.mock import patch

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


@patch("metagit.core.mcp.services.workspace_search.shutil.which", return_value=None)
def test_workspace_grep_excludes_node_modules(_mock_which: object) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp:
        root = Path(tmp)
        _write_grep_fixture(root)
        repo_dir = root / "platform" / "svc-a"
        nested = repo_dir / "node_modules" / "dep"
        nested.mkdir(parents=True)
        (nested / "index.js").write_text("grep-cli-marker\n", encoding="utf-8")
        result = runner.invoke(
            cli,
            ["workspace", "grep", "grep-cli-marker", "--json"],
            env=_env_workspace_root(root),
            catch_exceptions=False,
        )
    assert result.exit_code == 0
    assert result.output.count("grep-cli-marker") == 1


def test_workspace_grep_help_lists_scoped_examples() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["workspace", "grep", "--help"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "Whole workspace" in result.output
    assert "Single project" in result.output
    assert "grep info" in result.output


@patch("metagit.core.mcp.services.workspace_search.shutil.which", return_value=None)
def test_workspace_grep_info_without_rg(_mock_which: object) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp:
        root = Path(tmp)
        _write_grep_fixture(root)
        result = runner.invoke(
            cli,
            ["workspace", "grep", "info", "--json"],
            env=_env_workspace_root(root),
            catch_exceptions=False,
        )
    assert result.exit_code == 0
    assert '"ripgrep_available": false' in result.output
    assert '"search_backend": "python_walk"' in result.output


def test_workspace_grep_info_human_without_rg() -> None:
    import shutil

    if shutil.which("rg"):
        return
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp:
        root = Path(tmp)
        _write_grep_fixture(root)
        result = runner.invoke(
            cli,
            ["workspace", "grep", "info"],
            env=_env_workspace_root(root),
            catch_exceptions=False,
        )
    assert result.exit_code == 0
    assert "ripgrep: not found on PATH" in result.output
    assert "search backend: python_walk" in result.output


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

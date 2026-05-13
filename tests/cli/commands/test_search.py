#!/usr/bin/env python
"""
CLI tests for metagit search / find.
"""

from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def test_search_command_returns_json_matches() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path(".metagit.yml").write_text(
            "\n".join(
                [
                    "name: workspace",
                    "kind: application",
                    "workspace:",
                    "  projects:",
                    "    - name: platform",
                    "      repos:",
                    "        - name: abacus-app",
                    "          path: platform/abacus-app",
                    "          sync: true",
                    "          tags:",
                    "            code: abacus",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        repo_dir = Path("platform") / "abacus-app"
        repo_dir.mkdir(parents=True)
        (repo_dir / ".git").mkdir()
        result = runner.invoke(
            cli,
            ["search", "abacus", "--json"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    assert '"repo_name": "abacus-app"' in result.output


def test_find_alias_matches_search_command() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["find", "--help"])
    assert result.exit_code == 0
    assert (
        "metagit search" in result.output
        or "Search managed repositories" in result.output
    )

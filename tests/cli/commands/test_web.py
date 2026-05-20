#!/usr/bin/env python
"""CLI tests for metagit web commands."""

from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def test_web_serve_status_once(tmp_path: Path) -> None:
    runner = CliRunner()
    (tmp_path / ".metagit.yml").write_text(
        "name: workspace\nkind: application\n",
        encoding="utf-8",
    )
    (tmp_path / "metagit.config.yaml").write_text(
        "\n".join(
            [
                "config:",
                "  workspace:",
                "    path: ./sync",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        cli,
        [
            "--config",
            str(tmp_path / "metagit.config.yaml"),
            "web",
            "serve",
            "--root",
            str(tmp_path),
            "--status-once",
            "--port",
            "0",
        ],
    )
    assert result.exit_code == 0
    assert "web_state=ready" in result.output
    assert "url=http://" in result.output

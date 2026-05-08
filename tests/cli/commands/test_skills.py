#!/usr/bin/env python
"""
CLI tests for metagit skills commands.
"""

from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def test_skills_list_displays_bundled_skills() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["skills", "list"])
    assert result.exit_code == 0
    assert "running-gitnexus-analysis" in result.output


def test_skills_install_project_target_creates_skill_directory() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            ["skills", "install", "--scope", "project", "--target", "opencode"],
        )
        assert result.exit_code == 0
        destination = Path(".opencode/skills")
        assert destination.exists()
        assert any(item.is_dir() for item in destination.iterdir())

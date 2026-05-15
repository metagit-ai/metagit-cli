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
    assert "metagit-gitnexus" in result.output


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


def test_skills_install_single_skill_only() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "skills",
                "install",
                "--scope",
                "project",
                "--target",
                "opencode",
                "--skill",
                "metagit-projects",
            ],
        )
        assert result.exit_code == 0
        assert "Installed skill 'metagit-projects'" in result.output
        installed = [
            p.name for p in Path(".opencode/skills").iterdir() if p.is_dir()
        ]
        assert installed == ["metagit-projects"]


def test_skills_install_dry_run_does_not_write_files() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "skills",
                "install",
                "--scope",
                "project",
                "--target",
                "opencode",
                "--skill",
                "metagit-projects",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "dry run" in result.output
        assert "Would install skill 'metagit-projects'" in result.output
        assert not Path(".opencode/skills").exists()


def test_skills_install_unknown_skill_fails() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "skills",
            "install",
            "--target",
            "opencode",
            "--skill",
            "not-a-skill",
        ],
    )
    assert result.exit_code != 0
    assert "Unknown skill" in result.output

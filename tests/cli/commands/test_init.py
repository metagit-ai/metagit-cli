#!/usr/bin/env python
"""
CLI tests for metagit init command.
"""

import subprocess
from pathlib import Path

import yaml
from click.testing import CliRunner

from metagit.cli.commands.init import _resolve_project_metadata
from metagit.cli.main import cli


def test_resolve_project_metadata_non_git_directory(tmp_path: Path) -> None:
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    name, url = _resolve_project_metadata(project_dir)
    assert name == "my-project"
    assert url is None


def test_resolve_project_metadata_git_repo_without_remote(tmp_path: Path) -> None:
    project_dir = tmp_path / "local-repo"
    project_dir.mkdir()
    subprocess.run(["git", "init"], cwd=project_dir, check=True, capture_output=True)
    name, url = _resolve_project_metadata(project_dir)
    assert name == "local-repo"
    assert url is None


def test_init_succeeds_outside_git_repository() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            ["init", "--kind", "application", "--skip-gitignore"],
        )
        assert result.exit_code == 0, result.output
        config_path = Path(".metagit.yml")
        assert config_path.is_file()
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        assert loaded["name"] == Path.cwd().name
        assert "url" not in loaded

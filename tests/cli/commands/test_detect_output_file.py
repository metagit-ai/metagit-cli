#!/usr/bin/env python
"""CLI tests for detect --output-file compact status lines."""

import os
import subprocess
from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def _git_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    (root / "README.md").write_text("hello\n", encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname = "demo"\nversion = "0.0.1"\n', encoding="utf-8")
    subprocess.run(["git", "add", "README.md", "pyproject.toml"], cwd=root, check=True, capture_output=True)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True, env=env)
    return root


def test_detect_project_output_file_writes_payload_and_status_line(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "repo")
    out = repo / ".metagit" / ".detect" / "project.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "detect",
            "project",
            "--path",
            str(repo),
            "--output",
            "json",
            "--output-file",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "status=written" in result.output
    assert str(out.resolve()) in result.output
    assert out.is_file()
    payload = out.read_text(encoding="utf-8")
    assert payload.startswith("{")
    assert payload.strip() not in result.output


def test_detect_repo_map_output_file_is_compact(tmp_path: Path) -> None:
    target = tmp_path / "tree"
    target.mkdir()
    (target / "a.txt").write_text("x\n", encoding="utf-8")
    out = tmp_path / "repo_map.json"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["detect", "repo_map", "--path", str(target), "--output", "json", "--output-file", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert result.output.startswith("status=written")
    assert out.is_file()
    body = out.read_text(encoding="utf-8")
    assert "summary" in body
    assert "details" in body
    assert len(result.output) < out.stat().st_size

#!/usr/bin/env python
"""repo move infers the source project when -p is omitted."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from metagit import DEFAULT_CONFIG
from metagit.cli.main import cli

UNIQUE = """\
name: umbrella
kind: umbrella
workspace:
  projects:
    - name: billing
      repos:
        - name: api
          url: https://github.com/acme/api.git
    - name: other
      repos: []
"""

AMBIGUOUS = """\
name: umbrella
kind: umbrella
workspace:
  projects:
    - name: billing
      repos:
        - name: api
          url: https://github.com/acme/api.git
    - name: other
      repos:
        - name: api
          url: https://github.com/acme/api.git
"""


def test_move_infers_a_unique_project(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(UNIQUE, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--config",
            DEFAULT_CONFIG,
            "project",
            "-c",
            str(manifest),
            "repo",
            "move",
            "-n",
            "api",
            "--to-project",
            "other",
            "--manifest-only",
        ],
    )
    assert result.exit_code == 0, result.output
    text = manifest.read_text(encoding="utf-8")
    other = text.split("name: other", maxsplit=1)[1]
    billing = text.split("name: other", maxsplit=1)[0]
    assert "name: api" in other
    assert "name: api" not in billing


def test_move_reports_an_ambiguous_project_without_a_traceback(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(AMBIGUOUS, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--config",
            DEFAULT_CONFIG,
            "project",
            "-c",
            str(manifest),
            "repo",
            "move",
            "-n",
            "api",
            "--to-project",
            "third",
            "--manifest-only",
        ],
    )
    assert result.exit_code != 0
    assert "billing" in result.output
    assert "other" in result.output
    assert "-p/--project" in result.output
    assert "Traceback" not in result.output


def test_repo_list_without_project_does_not_traceback(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(UNIQUE, encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "project", "-c", str(manifest), "repo", "list"],
    )
    assert result.exit_code != 0
    assert "-p/--project" in result.output
    assert "Traceback" not in result.output

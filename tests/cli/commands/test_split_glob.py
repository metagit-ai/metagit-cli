#!/usr/bin/env python
"""Glob split keeps the root manifest out of project-add merge conflicts."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from click.testing import CliRunner

from metagit import DEFAULT_CONFIG
from metagit.cli.main import cli

MANIFEST = """\
name: umbrella
kind: umbrella
workspace:
  projects:
    - name: zeta
      repos: []
    - name: alpha
      repos: []
"""


def _git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    return subprocess.run(
        ["git", "-C", str(path), *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_glob_split_warns_and_project_add_merges(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(MANIFEST, encoding="utf-8")
    runner = CliRunner()
    split = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "config", "-c", str(manifest), "split", "--by", "all", "--glob"],
    )
    assert split.exit_code == 0, split.output
    combined = split.output + (getattr(split, "stderr", None) or "")
    assert "would reorder projects" in combined
    root = manifest.read_text(encoding="utf-8")
    assert ".metagit.d/projects/*.yml" in root
    assert "zeta.yml" not in root

    assert _git(tmp_path, "init", "-b", "main").returncode == 0
    assert _git(tmp_path, "add", ".").returncode == 0
    committed = _git(
        tmp_path,
        "-c",
        "user.email=test@example.com",
        "-c",
        "user.name=Test",
        "commit",
        "-m",
        "split",
    )
    assert committed.returncode == 0, committed.stderr
    base = manifest.read_text(encoding="utf-8")

    assert _git(tmp_path, "checkout", "-b", "add-left").returncode == 0
    left = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "project", "-c", str(manifest), "add", "left-side"],
    )
    assert left.exit_code == 0, left.output
    assert manifest.read_text(encoding="utf-8") == base
    assert (tmp_path / ".metagit.d" / "projects" / "left-side.yml").is_file()
    assert _git(tmp_path, "add", ".").returncode == 0
    assert (
        _git(
            tmp_path,
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test",
            "commit",
            "-m",
            "add left",
        ).returncode
        == 0
    )

    assert _git(tmp_path, "checkout", "main").returncode == 0
    assert _git(tmp_path, "checkout", "-b", "add-right").returncode == 0
    right = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "project", "-c", str(manifest), "add", "right-side"],
    )
    assert right.exit_code == 0, right.output
    assert manifest.read_text(encoding="utf-8") == base
    assert _git(tmp_path, "add", ".").returncode == 0
    assert (
        _git(
            tmp_path,
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test",
            "commit",
            "-m",
            "add right",
        ).returncode
        == 0
    )

    merged = _git(tmp_path, "merge", "add-left", "-m", "merge")
    assert merged.returncode == 0, merged.stdout + merged.stderr
    merged_root = manifest.read_text(encoding="utf-8")
    assert "<<<<<<<" not in merged_root
    assert merged_root == base
    assert (tmp_path / ".metagit.d" / "projects" / "left-side.yml").is_file()
    assert (tmp_path / ".metagit.d" / "projects" / "right-side.yml").is_file()

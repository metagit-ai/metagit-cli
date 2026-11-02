#!/usr/bin/env python
"""Discovered worktrees and merged-PR cleanup."""

from __future__ import annotations

import json
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
    - name: billing
      repos:
        - name: api
          path: repo
          sync: true
"""


def _git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True)


def _sha(path: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _workspace(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "--allow-empty", "-m", "init")
    feature = tmp_path / "feature"
    dirty = tmp_path / "dirty"
    _git(repo, "worktree", "add", "-b", "feature", str(feature))
    _git(
        feature,
        "-c",
        "user.email=test@example.com",
        "-c",
        "user.name=Test",
        "commit",
        "--allow-empty",
        "-m",
        "feature",
    )
    _git(feature, "branch", "-u", "main")
    _git(repo, "worktree", "add", "-b", "dirty", str(dirty))
    (dirty / "note.txt").write_text("uncommitted\n", encoding="utf-8")
    (tmp_path / ".metagit.yml").write_text(MANIFEST, encoding="utf-8")
    return feature, dirty, tmp_path / ".metagit.yml"


def test_discover_lists_plain_worktrees_and_gc_skips_dirty(tmp_path: Path, monkeypatch) -> None:
    feature, dirty, manifest = _workspace(tmp_path)
    heads = {"feature": _sha(feature), "dirty": _sha(dirty)}

    def lookup(_repo: str, _remote: str, branch: str) -> dict[str, str] | None:
        if branch not in heads:
            return None
        state = "merged" if branch == "feature" else "closed"
        return {"state": state, "head_sha": heads[branch]}

    monkeypatch.setattr("metagit.cli.commands.worktree.default_pr_lookup", lookup)
    runner = CliRunner()
    listed = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "worktree", "list", "--discover", "-c", str(manifest), "--json"],
    )
    assert listed.exit_code == 0, listed.output
    payload = json.loads(listed.output)
    by_branch = {item["branch"]: item for item in payload["worktrees"]}
    assert by_branch["feature"]["repo"] == "billing/api"
    assert by_branch["feature"]["dirty"] is False
    assert by_branch["feature"]["ahead"] == 1
    assert by_branch["main"]["primary"] is True
    assert by_branch["dirty"]["dirty"] is True

    preview = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "worktree", "gc", "--merged", "--dry-run", "-c", str(manifest), "--json"],
    )
    assert preview.exit_code == 0, preview.output
    planned = json.loads(preview.output)
    planned_paths = {Path(item["path"]).resolve() for item in planned["remove"]}
    assert feature.resolve() in planned_paths
    assert dirty.resolve() not in planned_paths
    assert feature.is_dir()
    assert dirty.is_dir()

    removed = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "worktree", "gc", "--merged", "-c", str(manifest), "--json"],
    )
    assert removed.exit_code == 0, removed.output
    assert not feature.exists()
    assert dirty.is_dir()
    assert (dirty / "note.txt").is_file()

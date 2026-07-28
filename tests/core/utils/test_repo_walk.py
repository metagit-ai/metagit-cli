#!/usr/bin/env python
"""Tests for ignore-aware repo file walking."""

from __future__ import annotations

from pathlib import Path

from metagit.core.utils.repo_walk import iter_repo_files


def test_iter_repo_files_skips_node_modules_and_venv(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "modules").mkdir(parents=True)
    (root / "modules" / "ok.tf").write_text('source = "../other"', encoding="utf-8")
    (root / "node_modules" / "pkg").mkdir(parents=True)
    (root / "node_modules" / "pkg" / "bad.tf").write_text("x", encoding="utf-8")
    (root / ".venv" / "lib").mkdir(parents=True)
    (root / ".venv" / "lib" / "bad.tf").write_text("x", encoding="utf-8")

    files, stats = iter_repo_files(root, suffix=".tf")
    rels = {str(p.relative_to(root)) for p in files}
    assert rels == {"modules/ok.tf"}
    assert stats.dirs_pruned >= 2


def test_iter_repo_files_honors_gitignore(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "keep").mkdir(parents=True)
    (root / "keep" / "a.tf").write_text("x", encoding="utf-8")
    (root / "secret").mkdir(parents=True)
    (root / "secret" / "b.tf").write_text("x", encoding="utf-8")
    (root / ".gitignore").write_text("secret/\n", encoding="utf-8")

    files, stats = iter_repo_files(root, suffix=".tf")
    rels = {str(p.relative_to(root)) for p in files}
    assert rels == {"keep/a.tf"}
    assert stats.files_skipped_gitignore >= 1 or stats.dirs_pruned >= 1

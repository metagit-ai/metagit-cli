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
    rels = {p.relative_to(root).as_posix() for p in files}
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
    rels = {p.relative_to(root).as_posix() for p in files}
    assert rels == {"keep/a.tf"}
    assert stats.files_skipped_gitignore >= 1 or stats.dirs_pruned >= 1


def test_iter_repo_files_scopes_nested_gitignore_to_owning_directory(
    tmp_path: Path,
) -> None:
    """Patterns from a/.gitignore must not leak into sibling directory b."""
    root = tmp_path / "repo"
    (root / "a").mkdir(parents=True)
    (root / "a" / ".gitignore").write_text("*.tf\n", encoding="utf-8")
    (root / "a" / "hidden.tf").write_text("x", encoding="utf-8")
    (root / "b").mkdir(parents=True)
    (root / "b" / "keep.tf").write_text("x", encoding="utf-8")

    files, _stats = iter_repo_files(root, suffix=".tf")
    rels = {p.relative_to(root).as_posix() for p in files}
    assert rels == {"b/keep.tf"}


def test_iter_repo_files_honors_gitignore_negation(tmp_path: Path) -> None:
    """A '!pattern' line re-includes a file an earlier deny pattern excluded."""
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    (root / ".gitignore").write_text("*.tf\n!keep.tf\n", encoding="utf-8")
    (root / "keep.tf").write_text("x", encoding="utf-8")
    (root / "drop.tf").write_text("x", encoding="utf-8")

    files, stats = iter_repo_files(root, suffix=".tf")
    rels = {p.relative_to(root).as_posix() for p in files}
    assert rels == {"keep.tf"}
    assert stats.files_skipped_gitignore == 1


def test_iter_repo_files_honors_gitignore_last_match_wins_within_file(
    tmp_path: Path,
) -> None:
    """A later deny pattern re-excludes a file an earlier '!' re-included (git parity)."""
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    (root / ".gitignore").write_text("!keep.tf\n*.tf\n", encoding="utf-8")
    (root / "keep.tf").write_text("x", encoding="utf-8")

    files, _stats = iter_repo_files(root, suffix=".tf")
    rels = {p.relative_to(root).as_posix() for p in files}
    assert rels == set()


def test_iter_repo_files_honors_gitignore_deeper_directory_overrides_ancestor(
    tmp_path: Path,
) -> None:
    """A deeper .gitignore's deny overrides an ancestor's negation (git parity).

    Root allows ``keep.tf`` back via ``!keep.tf``, but ``child/.gitignore`` denies
    all ``*.tf`` files again. Verified against ``git check-ignore``: the deeper
    rule, evaluated later, wins and ``child/keep.tf`` is ignored even though a
    same-named file at the root would not be.
    """
    root = tmp_path / "repo"
    (root / "child").mkdir(parents=True)
    (root / ".gitignore").write_text("!keep.tf\n", encoding="utf-8")
    (root / "child" / ".gitignore").write_text("*.tf\n", encoding="utf-8")
    (root / "keep.tf").write_text("x", encoding="utf-8")
    (root / "child" / "keep.tf").write_text("x", encoding="utf-8")

    files, _stats = iter_repo_files(root, suffix=".tf")
    rels = {p.relative_to(root).as_posix() for p in files}
    assert rels == {"keep.tf"}


def test_iter_repo_files_counts_only_suffix_matches_as_skipped(tmp_path: Path) -> None:
    """Ignore counters describe suffix-matching files, not the whole tree."""
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    (root / ".gitignore").write_text("ignored.*\n", encoding="utf-8")
    (root / "ignored.tf").write_text("x", encoding="utf-8")
    (root / "ignored.md").write_text("x", encoding="utf-8")
    (root / "keep.tf").write_text("x", encoding="utf-8")

    files, stats = iter_repo_files(root, suffix=".tf")
    rels = {p.relative_to(root).as_posix() for p in files}
    assert rels == {"keep.tf"}
    assert stats.files_skipped_gitignore == 1


def test_iter_repo_files_stops_at_max_files(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    for index in range(5):
        (root / f"m{index}.tf").write_text("x", encoding="utf-8")

    files, stats = iter_repo_files(root, suffix=".tf", max_files=2)
    assert len(files) == 2
    assert stats.files_yielded == 2


def test_iter_repo_files_skips_file_named_like_scaffold_segment(
    tmp_path: Path,
) -> None:
    """A file literally named 'node_modules' (not a dir) must still be skipped."""
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    (root / "node_modules").write_text("not a directory", encoding="utf-8")
    (root / "keep.txt").write_text("x", encoding="utf-8")

    files, stats = iter_repo_files(root)
    rels = {p.relative_to(root).as_posix() for p in files}
    assert rels == {"keep.txt"}
    assert stats.files_skipped_scaffold >= 1

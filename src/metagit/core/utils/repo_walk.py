#!/usr/bin/env python
"""Ignore-aware repository file walking."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from metagit.core.utils.files import parse_gitignore, should_ignore_path
from metagit.core.utils.scaffold_paths import (
    SCAFFOLD_PATH_SEGMENTS,
    path_has_scaffold_segment,
)


@dataclass
class RepoWalkStats:
    dirs_pruned: int = 0
    files_skipped_gitignore: int = 0
    files_skipped_scaffold: int = 0
    files_yielded: int = 0


def iter_repo_files(
    root: Path,
    *,
    suffix: str | None = None,
    max_files: int | None = None,
) -> tuple[list[Path], RepoWalkStats]:
    """
    Walk a repository tree, pruning scaffold dirs and gitignored paths during walk.

    Args:
        root: Repository root directory.
        suffix: When set, only yield files whose names end with this suffix.
        max_files: Stop yielding after this many files (early exit).

    Returns:
        Tuple of matched file paths and walk statistics.
    """
    stats = RepoWalkStats()
    files: list[Path] = []
    # Each directory's own .gitignore patterns are kept separately (never merged
    # into a global set) so they can be matched relative to the directory that
    # owns them and only applied to that directory's subtree.
    dir_patterns: dict[Path, set[str]] = {root: parse_gitignore(root / ".gitignore")}

    def _ancestors(current_dir: Path) -> list[Path]:
        try:
            rel_parts = current_dir.relative_to(root).parts
        except ValueError:
            rel_parts = ()
        ancestor = root
        chain = [root]
        for part in rel_parts:
            ancestor = ancestor / part
            chain.append(ancestor)
        return chain

    def _is_ignored(target: Path, current_dir: Path) -> bool:
        for ancestor in _ancestors(current_dir):
            patterns = dir_patterns.get(ancestor)
            if patterns and should_ignore_path(target, patterns, ancestor):
                return True
        return False

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(dirpath)
        if current not in dir_patterns:
            dir_patterns[current] = parse_gitignore(current / ".gitignore")

        scaffold_pruned = [name for name in dirnames if name in SCAFFOLD_PATH_SEGMENTS]
        if scaffold_pruned:
            stats.dirs_pruned += len(scaffold_pruned)
        dirnames[:] = [name for name in dirnames if name not in SCAFFOLD_PATH_SEGMENTS]

        ignored_dirs: list[str] = []
        kept_dirnames: list[str] = []
        for name in dirnames:
            subdir = current / name
            if _is_ignored(subdir, current):
                ignored_dirs.append(name)
            else:
                kept_dirnames.append(name)
        if ignored_dirs:
            stats.dirs_pruned += len(ignored_dirs)
        dirnames[:] = kept_dirnames

        for name in filenames:
            if max_files is not None and stats.files_yielded >= max_files:
                return files, stats

            file_path = current / name
            if _is_ignored(file_path, current):
                stats.files_skipped_gitignore += 1
                continue

            if path_has_scaffold_segment(str(file_path.relative_to(root))):
                stats.files_skipped_scaffold += 1
                continue

            if suffix is not None and not name.endswith(suffix):
                continue

            files.append(file_path)
            stats.files_yielded += 1

    return files, stats

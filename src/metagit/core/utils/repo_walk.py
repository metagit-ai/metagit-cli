#!/usr/bin/env python
"""Ignore-aware repository file walking."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from metagit.core.utils.files import parse_gitignore, should_ignore_path
from metagit.core.utils.scaffold_paths import SCAFFOLD_PATH_SEGMENTS


@dataclass
class RepoWalkStats:
    dirs_pruned: int = 0
    files_skipped_gitignore: int = 0
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
    ignore_patterns: set[str] = set()
    ignore_patterns.update(parse_gitignore(root / ".gitignore"))

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(dirpath)
        if current != root:
            ignore_patterns.update(parse_gitignore(current / ".gitignore"))

        scaffold_pruned = [name for name in dirnames if name in SCAFFOLD_PATH_SEGMENTS]
        if scaffold_pruned:
            stats.dirs_pruned += len(scaffold_pruned)
        dirnames[:] = [name for name in dirnames if name not in SCAFFOLD_PATH_SEGMENTS]

        ignored_dirs: list[str] = []
        kept_dirnames: list[str] = []
        for name in dirnames:
            subdir = current / name
            if should_ignore_path(subdir, ignore_patterns, root):
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
            if should_ignore_path(file_path, ignore_patterns, root):
                stats.files_skipped_gitignore += 1
                continue

            if suffix is not None and not name.endswith(suffix):
                continue

            files.append(file_path)
            stats.files_yielded += 1

    return files, stats

#!/usr/bin/env python
"""Ignore-aware repository file walking."""

from __future__ import annotations

import fnmatch
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from metagit.core.utils.scaffold_paths import (
    SCAFFOLD_PATH_SEGMENTS,
    path_has_scaffold_segment,
)


@dataclass
class RepoWalkStats:
    """Counters for one walk.

    ``files_skipped_gitignore`` and ``files_skipped_scaffold`` only count files that
    matched ``suffix``; non-matching files are discarded before any ignore checks run.
    """

    dirs_pruned: int = 0
    files_skipped_gitignore: int = 0
    files_skipped_scaffold: int = 0
    files_yielded: int = 0


def sum_scan_stats(stats_by_repo: Mapping[str, Mapping[str, int]]) -> dict[str, int]:
    """Sum per-repo walk counters into workspace totals, one entry per repo path."""
    totals: dict[str, int] = {}
    for stats in stats_by_repo.values():
        for key, value in stats.items():
            totals[key] = totals.get(key, 0) + value
    return totals


@dataclass
class _DirRules:
    """Ignore rules owned by a single directory, matched relative to it.

    ``rules`` preserves ``.gitignore`` line order (pattern, is_negation) so that
    last-match-wins semantics can be evaluated the same way ``git check-ignore``
    does.
    """

    base: Path
    rules: tuple[tuple[str, bool], ...] = ()

    def __bool__(self) -> bool:
        return bool(self.rules)


def _parse_gitignore_ordered(path: Path) -> tuple[tuple[str, bool], ...]:
    """Parse a .gitignore file into ``(pattern, is_negation)`` pairs, in file order."""
    if not path.exists():
        return ()

    rules: list[tuple[str, bool]] = []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                is_negation = line.startswith("!")
                pattern = (line[1:] if is_negation else line).rstrip("/")
                if pattern:
                    rules.append((pattern, is_negation))
    except OSError:
        return ()

    return tuple(rules)


def _dir_rules(directory: Path) -> _DirRules:
    """Load a directory's own .gitignore rules, preserving declaration order."""
    return _DirRules(base=directory, rules=_parse_gitignore_ordered(directory / ".gitignore"))


def _matches_pattern(target: Path, pattern: str, base: Path) -> bool:
    """Match a single gitignore-style pattern against a path relative to ``base``."""
    try:
        relative_str = str(target.relative_to(base))
    except ValueError:
        relative_str = target.name
    return fnmatch.fnmatch(relative_str, pattern) or fnmatch.fnmatch(target.name, pattern)


def _is_ignored(target: Path, chain: tuple[_DirRules, ...]) -> bool:
    """Return True when the last matching rule across the ancestor chain denies target.

    Rules are evaluated in order: ancestor directories before their descendants,
    and within each ``.gitignore`` in file order. The last matching rule decides
    the outcome, so a deeper directory's rules naturally override an ancestor's
    because they are evaluated later — matching ``git check-ignore``.
    """
    ignored = False
    for rules in chain:
        for pattern, is_negation in rules.rules:
            if _matches_pattern(target, pattern, rules.base):
                ignored = not is_negation
    return ignored


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
        suffix: When set, only yield files whose names end with this suffix. Files that
            do not match are skipped before ignore checks, so they cost nothing.
        max_files: Stop yielding after this many files (early exit).

    Returns:
        Tuple of matched file paths and walk statistics.
    """
    stats = RepoWalkStats()
    files: list[Path] = []
    # Each directory's own .gitignore patterns are kept separately (never merged
    # into a global set) so they can be matched relative to the directory that
    # owns them and only applied to that directory's subtree. The chain of
    # rule-bearing ancestors is built once per directory as the walk descends,
    # rather than rebuilt for every path that needs a check.
    chains: dict[Path, tuple[_DirRules, ...]] = {}

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current = Path(dirpath)
        parent_chain = () if current == root else chains.get(current.parent, ())
        own_rules = _dir_rules(current)
        chain = (*parent_chain, own_rules) if own_rules else parent_chain
        chains[current] = chain

        scaffold_pruned = [name for name in dirnames if name in SCAFFOLD_PATH_SEGMENTS]
        if scaffold_pruned:
            stats.dirs_pruned += len(scaffold_pruned)
        dirnames[:] = [name for name in dirnames if name not in SCAFFOLD_PATH_SEGMENTS]

        if chain:
            ignored_dirs: list[str] = []
            kept_dirnames: list[str] = []
            for name in dirnames:
                if _is_ignored(current / name, chain):
                    ignored_dirs.append(name)
                else:
                    kept_dirnames.append(name)
            if ignored_dirs:
                stats.dirs_pruned += len(ignored_dirs)
            dirnames[:] = kept_dirnames

        for name in filenames:
            if suffix is not None and not name.endswith(suffix):
                continue
            if max_files is not None and stats.files_yielded >= max_files:
                return files, stats

            file_path = current / name
            if chain and _is_ignored(file_path, chain):
                stats.files_skipped_gitignore += 1
                continue

            if path_has_scaffold_segment(str(file_path.relative_to(root))):
                stats.files_skipped_scaffold += 1
                continue

            files.append(file_path)
            stats.files_yielded += 1

    return files, stats

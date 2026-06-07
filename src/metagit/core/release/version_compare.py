#!/usr/bin/env python
"""Lightweight semver-ish version comparison without extra dependencies."""

from __future__ import annotations

import re


def _prerelease_key(prerelease: str) -> tuple[tuple[int, int | str], ...]:
    """Build a sortable key for prerelease suffixes like rc2 or rc10."""
    if not prerelease:
        return ()
    parts = re.split(r"(\d+)", prerelease.lower())
    key: list[tuple[int, int | str]] = []
    for part in parts:
        if not part:
            continue
        key.append((0, int(part)) if part.isdigit() else (1, part))
    return tuple(key)


def normalize_version(
    version: str,
) -> tuple[int, int, int, tuple[tuple[int, int | str], ...]]:
    """Return (major, minor, patch, prerelease_key) for ordering."""
    raw = version.strip().lstrip("vV")
    if not raw or raw in {"0.0.0", "unknown"}:
        return (0, 0, 0, ())
    main, _, prerelease = raw.partition("-")
    parts = re.split(r"[.+]", main)
    numbers: list[int] = []
    for part in parts[:3]:
        match = re.match(r"(\d+)", part or "")
        numbers.append(int(match.group(1)) if match else 0)
    while len(numbers) < 3:
        numbers.append(0)
    return (numbers[0], numbers[1], numbers[2], _prerelease_key(prerelease))


def compare_versions(left: str, right: str) -> int:
    """
    Compare two version strings.

    Returns -1 if left < right, 0 if equal, 1 if left > right.
    Release versions without a prerelease suffix rank above prereleases.
    """
    left_norm = normalize_version(left)
    right_norm = normalize_version(right)
    left_tuple = left_norm[:3]
    right_tuple = right_norm[:3]
    if left_tuple < right_tuple:
        return -1
    if left_tuple > right_tuple:
        return 1
    left_pre = left_norm[3]
    right_pre = right_norm[3]
    if not left_pre and right_pre:
        return 1
    if left_pre and not right_pre:
        return -1
    if left_pre < right_pre:
        return -1
    if left_pre > right_pre:
        return 1
    return 0

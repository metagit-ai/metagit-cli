#!/usr/bin/env python
"""Atlas secret and sensitive path exclusion helpers."""

from __future__ import annotations

import fnmatch
from pathlib import Path

_DEFAULT_PATTERNS: tuple[str, ...] = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "**/credentials*",
    "**/secrets/**",
    ".atlas/index/**",
)


def _matches_pattern(path: Path, pattern: str) -> bool:
    name = path.name
    parts = path.parts

    if pattern == ".env":
        return name == ".env"
    if pattern == ".env.*":
        return fnmatch.fnmatch(name, ".env.*")
    if pattern == "*.pem":
        return fnmatch.fnmatch(name, "*.pem")
    if pattern == "*.key":
        return fnmatch.fnmatch(name, "*.key")
    if pattern == "**/credentials*":
        return any(fnmatch.fnmatch(part, "credentials*") for part in parts)
    if pattern == "**/secrets/**":
        return "secrets" in parts[:-1]
    if pattern == ".atlas/index/**":
        for idx, part in enumerate(parts):
            if part == ".atlas" and idx + 1 < len(parts) and parts[idx + 1] == "index":
                return True
        return False

    return path.match(pattern)


def is_excluded_path(path: Path, *, patterns: tuple[str, ...] | None = None) -> bool:
    """Return True when ``path`` matches a sensitive-path exclusion pattern."""
    active = _DEFAULT_PATTERNS if patterns is None else patterns
    return any(_matches_pattern(path, pattern) for pattern in active)


__all__ = [
    "is_excluded_path",
]

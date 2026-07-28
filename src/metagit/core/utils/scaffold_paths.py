#!/usr/bin/env python
"""Shared scaffold path segment denylist for repo walks and search."""

from pathlib import Path

SCAFFOLD_PATH_SEGMENTS: frozenset[str] = frozenset(
    {
        ".git",
        ".metagit",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".tox",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        "out",
        ".next",
        ".nuxt",
        ".svelte-kit",
        "bower_components",
        "vendor",
        ".cache",
        ".turbo",
        ".parcel-cache",
        "coverage",
        "htmlcov",
        ".eggs",
        "site-packages",
        "__pypackages__",
        ".gradle",
        "target",
        ".yarn",
        ".pnpm",
    }
)


def path_has_scaffold_segment(file_path: str) -> bool:
    """True when any path component is local scaffolding (node_modules, .venv, …)."""
    if not file_path.strip():
        return False
    return bool(SCAFFOLD_PATH_SEGMENTS.intersection(Path(file_path).parts))

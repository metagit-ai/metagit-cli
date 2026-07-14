#!/usr/bin/env python
"""Atlas test discovery extractor."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path

from metagit.core.atlas.extractors.inventory import iter_repo_files

_EXTRACTOR = "tests-discovery@1.0.0"
_KIND = "test"


def _repo_root(repo_root: str | Path) -> Path:
    return Path(repo_root).resolve()


def _observed_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _relative_posix_path(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _is_test_file(path: Path) -> bool:
    name = path.name
    return name.startswith("test_") and name.endswith(".py") or name.endswith("_test.py")


def _test_locator(relative_path: str, function_name: str) -> str:
    return f"{relative_path}#{function_name}"


def _test_id(locator: str) -> str:
    return f"evidence:test:{locator}"


def _collect_test_functions(tree: ast.AST, relative_path: str) -> list[str]:
    locators: list[str] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            locators.append(_test_locator(relative_path, node.name))

    return locators


def discover_tests(repo_root: str | Path, revision: str) -> list[dict]:
    """Discover pytest-style test functions as evidence-shaped dictionaries."""
    root = _repo_root(repo_root)
    observed_at = _observed_at()
    tests: list[dict] = []

    for path in iter_repo_files(root):
        if path.suffix != ".py" or not _is_test_file(path):
            continue

        relative_path = _relative_posix_path(root, path)
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=relative_path)
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue

        for locator in _collect_test_functions(tree, relative_path):
            tests.append(
                {
                    "id": _test_id(locator),
                    "kind": _KIND,
                    "locator": locator,
                    "revision": revision,
                    "extractor": _EXTRACTOR,
                    "observedAt": observed_at,
                    "confidence": 1.0,
                }
            )

    tests.sort(key=lambda item: str(item["locator"]))
    return tests


__all__ = [
    "discover_tests",
]

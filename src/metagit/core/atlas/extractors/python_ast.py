#!/usr/bin/env python
"""Atlas Python AST symbol extractor."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path

from metagit.core.atlas.extractors.inventory import iter_repo_files

_EXTRACTOR = "python-ast@1.0.0"
_KIND = "symbol"


def _repo_root(repo_root: str | Path) -> Path:
    return Path(repo_root).resolve()


def _observed_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _relative_posix_path(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _symbol_locator(relative_path: str, qualified_name: str) -> str:
    return f"{relative_path}#{qualified_name}"


def _symbol_id(locator: str) -> str:
    return f"evidence:symbol:{locator}"


def _collect_symbols(tree: ast.AST, relative_path: str) -> list[str]:
    locators: list[str] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            locators.append(_symbol_locator(relative_path, node.name))
            continue
        if not isinstance(node, ast.ClassDef):
            continue

        locators.append(_symbol_locator(relative_path, node.name))
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                locators.append(_symbol_locator(relative_path, f"{node.name}.{item.name}"))

    return locators


def extract_python_symbols(repo_root: str | Path, revision: str) -> list[dict]:
    """Extract Python symbols as evidence-shaped dictionaries."""
    root = _repo_root(repo_root)
    observed_at = _observed_at()
    symbols: list[dict] = []

    for path in iter_repo_files(root):
        if path.suffix != ".py":
            continue

        relative_path = _relative_posix_path(root, path)
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=relative_path)
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue

        for locator in _collect_symbols(tree, relative_path):
            symbols.append(
                {
                    "id": _symbol_id(locator),
                    "kind": _KIND,
                    "locator": locator,
                    "revision": revision,
                    "extractor": _EXTRACTOR,
                    "observedAt": observed_at,
                    "confidence": 1.0,
                }
            )

    symbols.sort(key=lambda item: str(item["locator"]))
    return symbols


__all__ = [
    "extract_python_symbols",
]

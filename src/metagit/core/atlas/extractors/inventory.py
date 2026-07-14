#!/usr/bin/env python
"""Atlas repository file inventory extractor."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from metagit.core.atlas.extractors.secrets import is_excluded_path

_EXTRACTOR = "inventory@1.0.0"
_SKIP_DIRS = frozenset({
  ".git",
  "node_modules",
  "__pycache__",
  ".venv",
  ".tox",
  "dist",
  "build",
})
_LANGUAGE_BY_SUFFIX: dict[str, str] = {
  ".py": "python",
  ".js": "javascript",
  ".jsx": "javascript",
  ".ts": "typescript",
  ".tsx": "typescript",
  ".go": "go",
  ".rs": "rust",
  ".java": "java",
  ".kt": "kotlin",
  ".rb": "ruby",
  ".php": "php",
  ".cs": "csharp",
  ".cpp": "cpp",
  ".c": "c",
  ".h": "c",
  ".hpp": "cpp",
  ".swift": "swift",
  ".sh": "shell",
  ".zsh": "shell",
  ".bash": "shell",
  ".yaml": "yaml",
  ".yml": "yaml",
  ".json": "json",
  ".toml": "toml",
  ".md": "markdown",
  ".rst": "rst",
  ".sql": "sql",
  ".html": "html",
  ".css": "css",
}


def _repo_root(repo_root: str | Path) -> Path:
  return Path(repo_root).resolve()


def _observed_at() -> str:
  return (
    datetime.now(timezone.utc)
    .replace(microsecond=0)
    .isoformat()
    .replace("+00:00", "Z")
  )


def _relative_posix_path(repo_root: Path, path: Path) -> str:
  return path.relative_to(repo_root).as_posix()


def _language_hint(path: Path) -> str | None:
  return _LANGUAGE_BY_SUFFIX.get(path.suffix.lower())


def iter_repo_files(repo_root: str | Path) -> Iterator[Path]:
  """Yield repository files, skipping noise directories and excluded paths."""
  root = _repo_root(repo_root)

  def _walk(directory: Path) -> Iterator[Path]:
    for entry in sorted(directory.iterdir(), key=lambda item: item.name):
      if entry.is_dir():
        if entry.name in _SKIP_DIRS:
          continue
        yield from _walk(entry)
        continue
      if not entry.is_file():
        continue
      relative = Path(_relative_posix_path(root, entry))
      if is_excluded_path(relative):
        continue
      yield entry

  yield from _walk(root)


def build_inventory(repo_root: str | Path, revision: str) -> dict:
  """Build a sorted file inventory with language hints and provenance."""
  root = _repo_root(repo_root)
  files: list[dict[str, str | None]] = []

  for path in iter_repo_files(root):
    posix_path = _relative_posix_path(root, path)
    files.append({
      "path": posix_path,
      "language": _language_hint(path),
    })

  files.sort(key=lambda item: str(item["path"]))

  return {
    "files": files,
    "provenance": {
      "extractor": _EXTRACTOR,
      "revision": revision,
      "observedAt": _observed_at(),
    },
  }


__all__ = [
  "build_inventory",
  "iter_repo_files",
]

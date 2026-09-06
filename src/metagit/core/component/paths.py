#!/usr/bin/env python
"""Repository-relative component path normalization."""

from __future__ import annotations

from pathlib import PurePosixPath


def normalize_repo_relative_path(raw: str) -> str | ValueError:
    """
    Normalize a repository-relative component path to POSIX form.

    Returns ``.`` for the repository root. Rejects empty, absolute, and
    escaping (``..`` past root) paths. Does not touch the filesystem.
    """
    text = str(raw).strip().replace("\\", "/")
    if not text:
        return ValueError("component path is required")
    if text.startswith("/") or (len(text) >= 2 and text[0].isalpha() and text[1] == ":"):
        return ValueError("component path must be repository-relative")

    parts: list[str] = []
    for part in PurePosixPath(text).parts:
        if part == ".":
            continue
        if part == "..":
            if not parts:
                return ValueError("component path escapes repository root")
            parts.pop()
            continue
        parts.append(part)
    return "/".join(parts) if parts else "."

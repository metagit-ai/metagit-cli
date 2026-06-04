#!/usr/bin/env python
"""
Resolve manifest (definition), sync, and session roots for workspace operations.
"""

from __future__ import annotations

from pathlib import Path


def resolve_definition_root(definition_path: str) -> str:
    """Return the directory containing the workspace ``.metagit.yml`` manifest."""
    path = Path(definition_path).expanduser().resolve()
    if path.is_file():
        return str(path.parent)
    return str(path)


def resolve_sync_root(definition_root: str, workspace_path: str) -> str:
    """
    Return the sync root where project/repo mounts live.

    Relative ``workspace.path`` values resolve against ``definition_root``.
    """
    path = Path(workspace_path).expanduser()
    if path.is_absolute():
        return str(path.resolve())
    return str((Path(definition_root) / path).resolve())


def resolve_session_root(definition_root: str) -> str:
    """Return root for ``.metagit/sessions`` and ``.metagit/approvals`` state."""
    return str(Path(definition_root).expanduser().resolve())


__all__ = [
    "resolve_definition_root",
    "resolve_session_root",
    "resolve_sync_root",
]

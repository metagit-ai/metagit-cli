#!/usr/bin/env python
"""
Resolve manifest (definition), sync, and session roots for workspace operations.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_CAMPAIGNS_PATH = "_campaigns"


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


def resolve_campaigns_root(
    definition_root: str,
    campaigns_path: str | None = None,
) -> str:
    """
    Return the directory for committed campaign YAML overlays.

    Relative paths resolve from the manifest (definition) root. Defaults to
    ``_campaigns`` so the folder does not collide with workspace project names
    such as ``campaigns`` under the sync root.
    """
    resolved = campaigns_path or os.getenv("METAGIT_WORKSPACE_CAMPAIGNS_PATH") or DEFAULT_CAMPAIGNS_PATH
    candidate = Path(resolved).expanduser()
    base = Path(definition_root).expanduser().resolve()
    if candidate.is_absolute():
        return str(candidate.resolve())
    return str((base / candidate).resolve())


__all__ = [
    "DEFAULT_CAMPAIGNS_PATH",
    "resolve_campaigns_root",
    "resolve_definition_root",
    "resolve_session_root",
    "resolve_sync_root",
]

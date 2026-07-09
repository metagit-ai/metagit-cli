#!/usr/bin/env python
"""Resolve merge orchestrator persistence paths under the session root."""

from __future__ import annotations

from pathlib import Path

from metagit.core.workspace.root_resolver import resolve_session_root


def merges_root(session_root: str) -> Path:
    """Return ``.metagit/merges`` under the session root."""
    root = resolve_session_root(session_root)
    return Path(root) / ".metagit" / "merges"


def queue_file(session_root: str) -> Path:
    """Return the merge queue index path."""
    return merges_root(session_root) / "queue.json"


def merge_file(session_root: str, merge_id: str) -> Path:
    """Return the merge request document path."""
    return merges_root(session_root) / f"{merge_id}.json"


def events_file(session_root: str) -> Path:
    """Return the merge orchestrator event log path."""
    return Path(resolve_session_root(session_root)) / ".metagit" / "events" / "merge.jsonl"


__all__ = [
    "events_file",
    "merge_file",
    "merges_root",
    "queue_file",
]

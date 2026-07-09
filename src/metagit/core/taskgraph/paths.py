#!/usr/bin/env python
"""Resolve task-graph persistence paths under the session/manifest root."""

from __future__ import annotations

from pathlib import Path

from metagit.core.workspace.root_resolver import resolve_session_root


def tasks_root(session_root: str) -> Path:
    """Return ``.metagit/tasks`` under the session root."""
    root = resolve_session_root(session_root)
    return Path(root) / ".metagit" / "tasks"


def graphs_dir(session_root: str) -> Path:
    return tasks_root(session_root) / "graphs"


def graph_file(session_root: str, graph_id: str) -> Path:
    return graphs_dir(session_root) / f"{graph_id}.json"


def index_file(session_root: str) -> Path:
    return tasks_root(session_root) / "index.json"


def events_file(session_root: str) -> Path:
    return Path(resolve_session_root(session_root)) / ".metagit" / "events" / "taskgraph.jsonl"


__all__ = [
    "events_file",
    "graph_file",
    "graphs_dir",
    "index_file",
    "tasks_root",
]

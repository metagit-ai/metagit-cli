#!/usr/bin/env python
"""Resolve semantic graph persistence paths under the session/manifest root."""

from __future__ import annotations

from pathlib import Path

from metagit.core.workspace.root_resolver import resolve_session_root


def graph_root(session_root: str) -> Path:
    """Return ``.metagit/graph`` under the session root."""
    root = resolve_session_root(session_root)
    return Path(root) / ".metagit" / "graph"


def concepts_file(session_root: str) -> Path:
    """Return the semantic concept catalog path."""
    return graph_root(session_root) / "concepts.json"


def ownerships_file(session_root: str) -> Path:
    """Return the semantic ownership catalog path."""
    return graph_root(session_root) / "ownerships.json"


def ingest_hints_file(session_root: str) -> Path:
    """Return the deterministic semantic ingest hints path."""
    return graph_root(session_root) / "ingest-hints.json"


def events_file(session_root: str) -> Path:
    """Return the semantic event log path."""
    return Path(resolve_session_root(session_root)) / ".metagit" / "events" / "semantic.jsonl"


__all__ = [
    "concepts_file",
    "events_file",
    "graph_root",
    "ingest_hints_file",
    "ownerships_file",
]

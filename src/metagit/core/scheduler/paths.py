#!/usr/bin/env python
"""Resolve scheduler persistence paths under the session/manifest root."""

from __future__ import annotations

from pathlib import Path

from metagit.core.workspace.root_resolver import resolve_session_root


def schedule_root(session_root: str) -> Path:
    """Return ``.metagit/schedule`` under the session root."""
    root = resolve_session_root(session_root)
    return Path(root) / ".metagit" / "schedule"


def policy_file(session_root: str) -> Path:
    """Return the schedule policy path."""
    return schedule_root(session_root) / "policy.json"


def decisions_file(session_root: str) -> Path:
    """Return the schedule decisions JSONL path."""
    return schedule_root(session_root) / "decisions.jsonl"


def events_file(session_root: str) -> Path:
    """Return the scheduler event log path."""
    return Path(resolve_session_root(session_root)) / ".metagit" / "events" / "scheduler.jsonl"


__all__ = [
    "decisions_file",
    "events_file",
    "policy_file",
    "schedule_root",
]

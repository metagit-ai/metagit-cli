#!/usr/bin/env python
"""Resolve ACL persistence paths under the session/manifest root."""

from __future__ import annotations

from pathlib import Path

from metagit.core.workspace.root_resolver import resolve_session_root, resolve_worktrees_root


def coordination_root(session_root: str) -> Path:
    """Return ``.metagit`` under the session root."""
    root = resolve_session_root(session_root)
    return Path(root) / ".metagit"


def branches_dir(session_root: str) -> Path:
    return coordination_root(session_root) / "branches"


def leases_dir(session_root: str) -> Path:
    return coordination_root(session_root) / "leases"


def worktrees_dir(session_root: str) -> Path:
    return coordination_root(session_root) / "worktrees"


def claims_dir(session_root: str) -> Path:
    return coordination_root(session_root) / "claims"


def agents_dir(session_root: str) -> Path:
    return coordination_root(session_root) / "agents"


def events_dir(session_root: str) -> Path:
    return coordination_root(session_root) / "events"


def presence_dir(session_root: str) -> Path:
    return coordination_root(session_root) / "presence"


def branches_file(session_root: str) -> Path:
    return branches_dir(session_root) / "branches.json"


def leases_file(session_root: str) -> Path:
    return leases_dir(session_root) / "leases.json"


def worktrees_file(session_root: str) -> Path:
    return worktrees_dir(session_root) / "worktrees.json"


def claims_file(session_root: str) -> Path:
    return claims_dir(session_root) / "claims.json"


def presence_file(session_root: str) -> Path:
    return presence_dir(session_root) / "presence.json"


def events_file(session_root: str) -> Path:
    return events_dir(session_root) / "acl.jsonl"


def agent_manifest_file(session_root: str, agent_id: str) -> Path:
    return agents_dir(session_root) / f"{agent_id}.json"


def worktree_checkout_path(
    session_root: str,
    agent_id: str,
    project: str,
    repo: str,
    *,
    worktrees_path: str | None = None,
) -> Path:
    """Filesystem path for an agent worktree checkout."""
    root = resolve_worktrees_root(resolve_session_root(session_root), worktrees_path)
    return Path(root) / agent_id / project / repo


__all__ = [
    "agent_manifest_file",
    "agents_dir",
    "branches_dir",
    "branches_file",
    "claims_dir",
    "claims_file",
    "coordination_root",
    "events_dir",
    "events_file",
    "leases_dir",
    "leases_file",
    "presence_dir",
    "presence_file",
    "worktree_checkout_path",
    "worktrees_dir",
    "worktrees_file",
]

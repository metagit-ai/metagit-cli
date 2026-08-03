#!/usr/bin/env python
"""Namespace constants and identity helpers for the state plane."""

from __future__ import annotations

import hashlib
from pathlib import Path

NS_COORD_OBJECTIVES = "coord.objectives"
NS_COORD_HANDOFFS = "coord.handoffs"
NS_COORD_APPROVALS = "coord.approvals"
NS_COORD_EVENTS = "coord.events"

KEY_DOCUMENT = "document"

RESERVED_NAMESPACES: frozenset[str] = frozenset(
    {
        NS_COORD_OBJECTIVES,
        NS_COORD_HANDOFFS,
        NS_COORD_APPROVALS,
        NS_COORD_EVENTS,
        "acl.branches",
        "acl.leases",
        "acl.claims",
        "acl.worktrees",
        "acl.agents",
        "task.graphs",
        "schedule.policy",
        "merge.queue",
        "catalog.workspace",
    }
)


def default_org_id() -> str:
    return "_"


def derive_workspace_id(workspace_root: str) -> str:
    resolved = str(Path(workspace_root).expanduser().resolve())
    return hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:16]

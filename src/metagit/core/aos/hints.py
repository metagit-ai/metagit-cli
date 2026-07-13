#!/usr/bin/env python
"""Hint builders and ACL apply helpers for AOS next (RFC-0013)."""

from __future__ import annotations

import re
from typing import Any


def _slugify(value: str, *, fallback: str = "task") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or fallback


def decision_to_dict(decision: Any) -> dict[str, Any]:
    """Normalize a ScheduleDecision or fallback dict to a JSON-friendly dict."""
    if isinstance(decision, dict):
        return dict(decision)
    if hasattr(decision, "model_dump"):
        return decision.model_dump(mode="json")
    return {
        "decision_id": getattr(decision, "decision_id", None),
        "node_id": getattr(decision, "node_id", None),
        "graph_id": getattr(decision, "graph_id", None),
        "score": getattr(decision, "score", None),
    }


def hints_from_decision(decision: Any) -> tuple[str | None, list[str]]:
    """Extract compile_command and acl_commands from a decision-like object."""
    if isinstance(decision, dict):
        compile_command = decision.get("compile_command")
        acl_commands = list(decision.get("acl_commands") or [])
        return (str(compile_command) if compile_command else None, acl_commands)
    compile_command = getattr(decision, "compile_command", None)
    acl_commands = list(getattr(decision, "acl_commands", None) or [])
    return (compile_command, acl_commands)


def _dispatch_field(decision: Any, key: str) -> str | None:
    if isinstance(decision, dict):
        hints = decision.get("dispatch_hints") or {}
        value = hints.get(key)
        return str(value) if value else None
    hints = getattr(decision, "dispatch_hints", None) or {}
    if isinstance(hints, dict):
        value = hints.get(key)
        return str(value) if value else None
    return None


def apply_acl_binds(
    session_root: str,
    *,
    agent_id: str,
    decision: Any,
    pattern: str = "**/*",
) -> list[str] | Exception:
    """Execute ACL allocate/lease/worktree/claim for the chosen decision node."""
    from metagit.core.coordination.claim_service import ClaimService
    from metagit.core.coordination.lease_service import LeaseService
    from metagit.core.coordination.models import FileClaim
    from metagit.core.coordination.worktree_service import WorktreeService

    repository = _dispatch_field(decision, "repository")
    title = _dispatch_field(decision, "title") or "task"
    if isinstance(decision, dict):
        task_id = str(decision.get("node_id") or "")
    else:
        task_id = str(getattr(decision, "node_id", "") or "")
    if not repository or not task_id:
        return ValueError("apply-hints requires decision dispatch_hints.repository and node_id")

    desc = _slugify(title, fallback=task_id)
    applied: list[str] = []

    lease = LeaseService(session_root).acquire(
        repository=repository,
        agent_id=agent_id,
        task_id=task_id,
        allocate_if_missing=True,
        description=desc,
    )
    if isinstance(lease, Exception):
        return lease
    applied.append(f"lease:{lease.lease_id}")

    worktree = WorktreeService(session_root).create(
        repository=repository,
        agent_id=agent_id,
        task_id=task_id,
        branch=lease.branch,
        lease_id=lease.lease_id,
    )
    if isinstance(worktree, Exception):
        return worktree
    applied.append(f"worktree:{worktree.worktree_id}")

    claim = ClaimService(session_root).declare(
        repository=repository,
        agent_id=agent_id,
        patterns=[pattern],
        task_id=task_id,
    )
    if isinstance(claim, Exception):
        return claim
    if isinstance(claim, FileClaim):
        applied.append(f"claim:{claim.claim_id}")
    return applied


__all__ = ["apply_acl_binds", "decision_to_dict", "hints_from_decision"]

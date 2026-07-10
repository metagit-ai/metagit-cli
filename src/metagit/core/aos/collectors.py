#!/usr/bin/env python
"""Default subsystem collectors wrapping existing RFC-0007–0012 services."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from metagit.core.aos.models import AosSubsystemSection


class DefaultSubsystemCollector:
    """Best-effort collectors; missing packages degrade to available=False."""

    def __init__(self, session_root: str) -> None:
        self._session_root = str(Path(session_root).expanduser().resolve())

    def collect_all(self) -> dict[str, AosSubsystemSection]:
        return {
            "acl": self._collect_acl(),
            "taskgraph": self._collect_taskgraph(),
            "context_compile": self._collect_context_compile(),
            "semantic": self._collect_semantic(),
            "merge": self._collect_merge(),
            "scheduler": self._collect_scheduler(),
        }

    def _collect_acl(self) -> AosSubsystemSection:
        try:
            from metagit.core.coordination.claim_service import ClaimService
            from metagit.core.coordination.lease_service import LeaseService
            from metagit.core.coordination.worktree_service import WorktreeService
        except Exception as exc:  # noqa: BLE001 — soft degrade
            return AosSubsystemSection(available=False, summary={"error": str(exc)})

        leases = LeaseService(self._session_root).list()
        if isinstance(leases, Exception):
            return AosSubsystemSection(available=False, summary={"error": str(leases)})
        worktrees = WorktreeService(self._session_root).list()
        if isinstance(worktrees, Exception):
            return AosSubsystemSection(available=False, summary={"error": str(worktrees)})
        claims = ClaimService(self._session_root).list()
        if isinstance(claims, Exception):
            return AosSubsystemSection(available=False, summary={"error": str(claims)})

        lease_status = Counter(row.status for row in leases.leases)
        wt_status = Counter(row.status for row in worktrees.worktrees)
        active_claims = sum(1 for row in claims.claims if row.status == "active")
        return AosSubsystemSection(
            available=True,
            summary={
                "leases_active": lease_status.get("active", 0),
                "leases_expired": lease_status.get("expired", 0),
                "worktrees_active": wt_status.get("active", 0),
                "claims_active": active_claims,
            },
        )

    def _collect_taskgraph(self) -> AosSubsystemSection:
        try:
            from metagit.core.taskgraph.service import TaskGraphService
        except Exception as exc:  # noqa: BLE001
            return AosSubsystemSection(available=False, summary={"error": str(exc)})

        service = TaskGraphService(self._session_root)
        nodes = service.list_nodes()
        if isinstance(nodes, Exception):
            return AosSubsystemSection(available=False, summary={"error": str(nodes)})
        by_status = Counter(node.status for node in nodes)
        ready = service.ready()
        ready_count = 0 if isinstance(ready, Exception) else len(ready)
        return AosSubsystemSection(
            available=True,
            summary={
                "ready": ready_count,
                "blocked": by_status.get("blocked", 0),
                "running": by_status.get("running", 0),
                "pending": by_status.get("pending", 0),
                "completed": by_status.get("completed", 0),
                "total_nodes": len(nodes),
            },
        )

    def _collect_context_compile(self) -> AosSubsystemSection:
        try:
            import metagit.core.context.compiler as _compiler  # noqa: F401
        except Exception as exc:  # noqa: BLE001
            return AosSubsystemSection(available=False, summary={"error": str(exc)})
        return AosSubsystemSection(available=True, summary={})

    def _collect_semantic(self) -> AosSubsystemSection:
        try:
            from metagit.core.semantic.store import SemanticGraphStore
        except Exception as exc:  # noqa: BLE001
            return AosSubsystemSection(available=False, summary={"error": str(exc)})
        store = SemanticGraphStore(self._session_root)
        concepts = store.load_concepts()
        if isinstance(concepts, Exception):
            return AosSubsystemSection(available=False, summary={"error": str(concepts)})
        ownerships = store.load_ownerships()
        if isinstance(ownerships, Exception):
            return AosSubsystemSection(available=False, summary={"error": str(ownerships)})
        return AosSubsystemSection(
            available=True,
            summary={"concepts": len(concepts), "ownerships": len(ownerships)},
        )

    def _collect_merge(self) -> AosSubsystemSection:
        try:
            from metagit.core.merge.service import MergeOrchestrator
        except Exception as exc:  # noqa: BLE001
            return AosSubsystemSection(available=False, summary={"error": str(exc)})
        rows = MergeOrchestrator(self._session_root).status()
        if isinstance(rows, Exception):
            return AosSubsystemSection(available=False, summary={"error": str(rows)})
        by_status = Counter(getattr(row, "status", "unknown") for row in rows)
        return AosSubsystemSection(
            available=True,
            summary={
                "queued": by_status.get("queued", 0),
                "running": by_status.get("running", 0),
                "conflict": by_status.get("conflict", 0) + by_status.get("failed", 0),
                "total": len(rows),
            },
        )

    def _collect_scheduler(self) -> AosSubsystemSection:
        try:
            from metagit.core.scheduler.service import SchedulerService
        except Exception as exc:  # noqa: BLE001
            return AosSubsystemSection(available=False, summary={"error": str(exc)})
        status = SchedulerService(self._session_root).status(recent=5)
        if isinstance(status, Exception):
            return AosSubsystemSection(available=False, summary={"error": str(status)})
        recent_ids = [d.decision_id for d in status.recent_decisions]
        return AosSubsystemSection(
            available=True,
            summary={
                "ready_count": status.ready_count,
                "recent_decision_ids": recent_ids,
                "merge_pressure": status.merge_pressure,
            },
        )


__all__ = ["DefaultSubsystemCollector"]

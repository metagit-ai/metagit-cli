#!/usr/bin/env python
"""AosService — status / doctor / next composition façade (RFC-0013)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol

from metagit.core.aos.collectors import DefaultSubsystemCollector
from metagit.core.aos.events import AosEventStore
from metagit.core.aos.models import (
    AosDoctorResult,
    AosFinding,
    AosHeartbeatResult,
    AosNextResult,
    AosRecoverResult,
    AosStatusResult,
    AosSubsystemSection,
)
from metagit.core.aos.protocols import SubsystemCollector
from metagit.core.aos.recovery import build_recovery_recipes, enrich_findings
from metagit.core.workspace.context_models import utc_now_iso


class _SchedulerLike(Protocol):
    def preview_next(self, graph_id: str | None = None, *, limit: int = 1) -> list[Any] | Exception: ...

    def next(self, graph_id: str | None = None, *, limit: int = 1) -> list[Any] | Exception: ...


FixFn = Callable[["AosService"], list[str] | Exception]
ApplyAclFn = Callable[..., list[str] | Exception]


class AosService:
    """Thin aggregator over ACL, task graph, and optional 0009–0012 services."""

    def __init__(
        self,
        session_root: str,
        *,
        collectors: SubsystemCollector | None = None,
        scheduler: _SchedulerLike | None = None,
        fix_fn: FixFn | None = None,
        apply_acl_fn: ApplyAclFn | None = None,
        now_fn: Callable[[], str] | None = None,
    ) -> None:
        self._session_root = str(Path(session_root).expanduser().resolve())
        self._collectors = collectors or DefaultSubsystemCollector(self._session_root)
        self._scheduler = scheduler
        self._fix_fn = fix_fn
        self._apply_acl_fn = apply_acl_fn
        self._now = now_fn or utc_now_iso

    def status(self) -> AosStatusResult | Exception:
        try:
            sections = self._collectors.collect_all()
        except Exception as exc:  # noqa: BLE001
            return exc
        return AosStatusResult(generated_at=self._now(), subsystems=sections)

    def doctor(self, *, fix: bool = False, confirm: bool = False) -> AosDoctorResult | Exception:
        if fix and not confirm:
            return ValueError("doctor --fix requires --yes (confirm=true)")
        snap = self.status()
        if isinstance(snap, Exception):
            return snap
        findings, suggestions = self._analyze(snap.subsystems)
        findings.extend(enrich_findings(snap.subsystems))
        recipes = build_recovery_recipes(findings)
        for recipe in recipes:
            if recipe.command not in suggestions:
                suggestions.append(recipe.command)
        fixed: list[str] = []
        if fix and confirm:
            result = self._fix_fn(self) if self._fix_fn is not None else self._default_fix()
            if isinstance(result, Exception):
                return result
            fixed = list(result)
            refreshed = self.status()
            if not isinstance(refreshed, Exception):
                snap = refreshed
                findings, suggestions = self._analyze(snap.subsystems)
                findings.extend(enrich_findings(snap.subsystems))
                recipes = build_recovery_recipes(findings)
                for recipe in recipes:
                    if recipe.command not in suggestions:
                        suggestions.append(recipe.command)
        return AosDoctorResult(
            generated_at=self._now(),
            subsystems=snap.subsystems,
            findings=findings,
            suggested_commands=suggestions,
            fixed=fixed,
            recovery_recipes=recipes,
        )

    def recover(
        self,
        *,
        agent_id: str,
        confirm: bool = False,
        release_orphan_claims: bool = False,
        cancel_stale_merges: bool = False,
    ) -> AosRecoverResult | Exception:
        if not confirm:
            return ValueError("recover requires --yes (confirm=true)")
        if not agent_id.strip():
            return ValueError("recover requires --agent-id")
        actions: list[str] = []
        skipped: list[str] = []
        errors: list[str] = []

        fix = self._default_fix()
        if isinstance(fix, Exception):
            return fix
        actions.extend(fix)

        reset = self._reset_stuck_tasks(agent_id=agent_id)
        if isinstance(reset, Exception):
            errors.append(str(reset))
        else:
            actions.extend(reset)

        if release_orphan_claims:
            released = self._release_orphan_claims(agent_id=agent_id)
            if isinstance(released, Exception):
                errors.append(str(released))
            else:
                actions.extend(released)
        else:
            skipped.append("release_orphan_claims_requires_flag")

        if cancel_stale_merges:
            skipped.append("cancel_stale_merges_not_implemented")
        else:
            skipped.append("cancel_stale_merges_requires_flag")

        AosEventStore(self._session_root).append(
            "aos.recover",
            {
                "agent_id": agent_id,
                "actions": actions,
                "skipped": skipped,
                "errors": errors,
            },
        )
        return AosRecoverResult(
            generated_at=self._now(),
            agent_id=agent_id,
            actions=actions,
            skipped=skipped,
            errors=errors,
        )

    def heartbeat(self, *, agent_id: str, ttl: str = "1h") -> AosHeartbeatResult | Exception:
        if not agent_id.strip():
            return ValueError("heartbeat requires --agent-id")
        renewed: list[str] = []
        errors: list[str] = []
        try:
            from metagit.core.coordination.lease_service import LeaseService
        except Exception as exc:  # noqa: BLE001
            return exc
        service = LeaseService(self._session_root)
        listed = service.list(agent_id=agent_id)
        if isinstance(listed, Exception):
            return listed
        for row in listed.leases:
            if row.status != "active":
                continue
            result = service.renew(lease_id=row.lease_id, agent_id=agent_id, ttl=ttl)
            if isinstance(result, Exception):
                errors.append(f"{row.lease_id}:{result}")
            else:
                renewed.append(row.lease_id)
        AosEventStore(self._session_root).append(
            "aos.heartbeat",
            {"agent_id": agent_id, "renewed": renewed, "errors": errors},
        )
        return AosHeartbeatResult(
            generated_at=self._now(),
            agent_id=agent_id,
            renewed=renewed,
            errors=errors,
        )

    def _reset_stuck_tasks(self, *, agent_id: str) -> list[str] | Exception:
        try:
            from metagit.core.taskgraph.service import TaskGraphService
        except Exception as exc:  # noqa: BLE001
            return [f"taskgraph_unavailable:{exc}"]
        service = TaskGraphService(self._session_root)
        nodes = service.list_nodes(status="running")
        if isinstance(nodes, Exception):
            return nodes
        actions: list[str] = []
        for node in nodes:
            if node.agent_id and node.agent_id != agent_id:
                continue
            result = service._set_status(node.node_id, "ready", graph_id=node.graph_id)
            if isinstance(result, Exception):
                return result
            actions.append(f"task_reset_ready:{node.node_id}")
        return actions

    def _release_orphan_claims(self, *, agent_id: str) -> list[str] | Exception:
        try:
            from metagit.core.coordination.claim_service import ClaimService
        except Exception as exc:  # noqa: BLE001
            return [f"claims_unavailable:{exc}"]
        service = ClaimService(self._session_root)
        listed = service.list(agent_id=agent_id, status="active")
        if isinstance(listed, Exception):
            return listed
        actions: list[str] = []
        for claim in listed.claims:
            result = service.release(claim_id=claim.claim_id, agent_id=agent_id)
            if isinstance(result, Exception):
                return result
            actions.append(f"claim_released:{claim.claim_id}")
        return actions

    def next(
        self,
        *,
        commit: bool = False,
        apply_hints: bool = False,
        agent_id: str | None = None,
        graph_id: str | None = None,
        limit: int = 1,
    ) -> AosNextResult | Exception:
        from metagit.core.aos.hints import apply_acl_binds, decision_to_dict, hints_from_decision

        if apply_hints and not agent_id:
            return ValueError("--apply-hints requires --agent-id")

        scheduler = self._scheduler
        scheduler_available = True
        if scheduler is None:
            try:
                from metagit.core.scheduler.service import SchedulerService

                scheduler = SchedulerService(self._session_root)
            except Exception:  # noqa: BLE001
                scheduler_available = False
                scheduler = None

        decisions: list[Any] = []
        committed = False
        reasons: list[str] = []

        if scheduler is not None and scheduler_available:
            if commit:
                result = scheduler.next(graph_id, limit=limit)
                committed = True
            else:
                result = scheduler.preview_next(graph_id, limit=limit)
            if isinstance(result, Exception):
                return result
            decisions = list(result)
        else:
            scheduler_available = False
            fallback = self._fallback_ready(graph_id)
            if isinstance(fallback, Exception):
                return fallback
            decisions = fallback
            reasons.append("scheduler_unavailable_fallback_ready")

        if not decisions:
            return AosNextResult(
                generated_at=self._now(),
                committed=committed,
                hints_applied=False,
                scheduler_available=scheduler_available,
                reasons=reasons + ["empty_ready_set"],
            )

        decision = decisions[0]
        compile_command, acl_commands = hints_from_decision(decision)
        decision_dict = decision_to_dict(decision)
        hints_applied = False
        if apply_hints:
            assert agent_id is not None
            binder = self._apply_acl_fn or apply_acl_binds
            applied = binder(
                self._session_root,
                agent_id=agent_id,
                decision=decision,
            )
            if isinstance(applied, Exception):
                return applied
            hints_applied = True
            reasons.extend(applied)

        return AosNextResult(
            generated_at=self._now(),
            decision=decision_dict,
            compile_command=compile_command,
            acl_commands=acl_commands,
            committed=committed,
            hints_applied=hints_applied,
            scheduler_available=scheduler_available,
            reasons=reasons,
        )

    def _analyze(self, subsystems: dict[str, AosSubsystemSection]) -> tuple[list[AosFinding], list[str]]:
        findings: list[AosFinding] = []
        suggestions: list[str] = []
        acl = subsystems.get("acl")
        if acl and acl.available:
            expired = int(acl.summary.get("leases_expired") or 0)
            if expired > 0:
                findings.append(
                    AosFinding(
                        severity="warning",
                        code="stale_lease",
                        message=f"{expired} expired lease(s) present",
                        subsystem="acl",
                    )
                )
                suggestions.append("metagit lease list --json")
                suggestions.append("metagit worktree gc")
            active_wt = int(acl.summary.get("worktrees_active") or 0)
            if active_wt > 0 and expired > 0:
                findings.append(
                    AosFinding(
                        severity="warning",
                        code="orphan_worktree_risk",
                        message="active worktrees may outlive expired leases",
                        subsystem="acl",
                    )
                )
                suggestions.append("metagit worktree gc")

        task = subsystems.get("taskgraph")
        if task and task.available:
            blocked = int(task.summary.get("blocked") or 0)
            ready = int(task.summary.get("ready") or 0)
            if blocked > 0:
                findings.append(
                    AosFinding(
                        severity="warning",
                        code="blocked_tasks",
                        message=f"{blocked} blocked task node(s)",
                        subsystem="taskgraph",
                    )
                )
                suggestions.append("metagit task list --status blocked --json")
            if ready == 0:
                findings.append(
                    AosFinding(
                        severity="info",
                        code="empty_ready_set",
                        message="no ready task nodes",
                        subsystem="taskgraph",
                    )
                )

        for key in ("context_compile", "semantic", "merge", "scheduler"):
            section = subsystems.get(key)
            if section is not None and not section.available:
                findings.append(
                    AosFinding(
                        severity="info",
                        code="subsystem_unavailable",
                        message=f"{key} not available in this workspace",
                        subsystem=key,
                    )
                )

        merge = subsystems.get("merge")
        if merge and merge.available:
            pressure = int(merge.summary.get("queued") or 0) + int(merge.summary.get("running") or 0)
            if pressure >= 3:
                findings.append(
                    AosFinding(
                        severity="warning",
                        code="merge_pressure",
                        message=f"merge queue depth {pressure}",
                        subsystem="merge",
                    )
                )
                suggestions.append("metagit merge status --json")

        # de-dupe suggestions preserving order
        seen: set[str] = set()
        unique = []
        for cmd in suggestions:
            if cmd not in seen:
                seen.add(cmd)
                unique.append(cmd)
        return findings, unique

    def _default_fix(self) -> list[str]:
        fixed: list[str] = []
        try:
            from metagit.core.coordination.lease_service import LeaseService
            from metagit.core.coordination.worktree_service import WorktreeService
        except Exception as exc:  # noqa: BLE001
            return [f"acl_unavailable:{exc}"]

        leases = LeaseService(self._session_root).list()
        if not isinstance(leases, Exception):
            expired = [row.lease_id for row in leases.leases if row.status == "expired"]
            for lease_id in expired:
                fixed.append(f"lease_expired:{lease_id}")

        destroyed = WorktreeService(self._session_root).gc()
        if isinstance(destroyed, Exception):
            return destroyed
        for row in destroyed:
            fixed.append(f"worktree_destroyed:{row.worktree_id}")
        return fixed

    def _fallback_ready(self, graph_id: str | None) -> list[dict[str, Any]] | Exception:
        try:
            from metagit.core.taskgraph.service import TaskGraphService
        except Exception as exc:  # noqa: BLE001
            return exc
        ready = TaskGraphService(self._session_root).ready(graph_id)
        if isinstance(ready, Exception):
            return ready
        if not ready:
            return []
        node = ready[0]
        compile_command = None
        if node.project and node.repository:
            repo_name = node.repository.split("/")[-1]
            compile_command = (
                f"metagit context compile --project {node.project} --repo {repo_name} --task-id {node.node_id}"
            )
        acl_commands: list[str] = []
        if node.acl is not None:
            acl_commands = list(node.acl.acl_commands)
        return [
            {
                "decision_id": f"fallback-{node.node_id}",
                "at": self._now(),
                "graph_id": node.graph_id,
                "node_id": node.node_id,
                "score": 0.0,
                "reasons": ["fallback_ready"],
                "dispatch_hints": {
                    "title": node.title,
                    "project": node.project,
                    "repository": node.repository,
                },
                "acl_commands": acl_commands,
                "compile_command": compile_command,
                "skipped": False,
            }
        ]


__all__ = ["AosService"]

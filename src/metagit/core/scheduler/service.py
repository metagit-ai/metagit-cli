#!/usr/bin/env python
"""Service layer for scoring ready tasks and emitting schedule decisions."""

from __future__ import annotations

import uuid
from collections import Counter
from typing import Any, Callable

from metagit.core.scheduler.events import ScheduleEventStore
from metagit.core.scheduler.models import (
    ScheduleDecision,
    SchedulePolicy,
    ScheduleStatus,
    ScheduleWeightOverrides,
    ScheduleWeights,
)
from metagit.core.scheduler.scoring import rank_candidates, score_node
from metagit.core.scheduler.store import ScheduleStore
from metagit.core.taskgraph.models import TaskNode
from metagit.core.taskgraph.service import TaskGraphService
from metagit.core.workspace.context_models import utc_now_iso

ReadyFn = Callable[[str | None], list[TaskNode] | Exception]
WorktreesFn = Callable[[], list[Any] | Exception]
MergeStatusFn = Callable[[], list[Any] | Exception]


class SchedulerService:
    """Choose which ready task node should run next (no git / no model launch)."""

    def __init__(
        self,
        session_root: str,
        *,
        store: ScheduleStore | None = None,
        event_store: ScheduleEventStore | None = None,
        task_service: TaskGraphService | None = None,
        ready_fn: ReadyFn | None = None,
        worktrees_fn: WorktreesFn | None = None,
        merge_status_fn: MergeStatusFn | None = None,
        now_fn: Callable[[], str] | None = None,
    ) -> None:
        self._session_root = session_root
        self.store = store or ScheduleStore(session_root)
        self._events = event_store or ScheduleEventStore(session_root)
        self._tasks = task_service or TaskGraphService(session_root)
        self._ready_fn = ready_fn
        self._worktrees_fn = worktrees_fn
        self._merge_status_fn = merge_status_fn
        self._now = now_fn or utc_now_iso

    def policy_show(self) -> SchedulePolicy | Exception:
        return self.store.load_policy()

    def policy_set(
        self,
        *,
        weights: dict[str, float] | None = None,
        merge_queue_threshold: int | None = None,
        merge_pressure_penalty: float | None = None,
        skip_on_merge_pressure: bool | None = None,
        graph_id: str | None = None,
        graph_weights: dict[str, float] | None = None,
    ) -> SchedulePolicy | Exception:
        policy = self.store.load_policy()
        if isinstance(policy, Exception):
            return policy
        if weights:
            current = policy.weights.model_dump()
            current.update({k: float(v) for k, v in weights.items() if k in current})
            policy.weights = ScheduleWeights.model_validate(current)
        if merge_queue_threshold is not None:
            policy.merge_queue_threshold = merge_queue_threshold
        if merge_pressure_penalty is not None:
            policy.merge_pressure_penalty = merge_pressure_penalty
        if skip_on_merge_pressure is not None:
            policy.skip_on_merge_pressure = skip_on_merge_pressure
        if graph_id and graph_weights:
            existing = policy.graph_overrides.get(graph_id) or ScheduleWeightOverrides()
            data = existing.model_dump()
            for key, value in graph_weights.items():
                if key in data:
                    data[key] = float(value)
            policy.graph_overrides[graph_id] = ScheduleWeightOverrides.model_validate(data)
        saved = self.store.save_policy(policy)
        if isinstance(saved, Exception):
            return saved
        return policy

    def preview_next(self, graph_id: str | None = None, *, limit: int = 1) -> list[ScheduleDecision] | Exception:
        """Same ranking as ``next()``, but do not append decisions or emit events."""
        return self._select_next(graph_id, limit=limit, persist=False)

    def next(self, graph_id: str | None = None, *, limit: int = 1) -> list[ScheduleDecision] | Exception:
        return self._select_next(graph_id, limit=limit, persist=True)

    def _select_next(
        self,
        graph_id: str | None,
        *,
        limit: int,
        persist: bool,
    ) -> list[ScheduleDecision] | Exception:
        if limit < 1:
            return ValueError("limit must be >= 1")
        policy = self.store.load_policy()
        if isinstance(policy, Exception):
            return policy
        ready = self._ready(graph_id)
        if isinstance(ready, Exception):
            return ready
        if not ready:
            return []

        warm = self._warm_repos()
        if isinstance(warm, Exception):
            return warm
        depths = self._merge_depths()
        if isinstance(depths, Exception):
            return depths
        under = self._underrepresented_repos(ready, policy)
        if isinstance(under, Exception):
            return under

        scored = [
            score_node(
                node,
                policy=policy,
                warm_repos=warm,
                underrepresented_repos=under,
                merge_depth_by_repo=depths,
            )
            for node in ready
        ]
        ranked = rank_candidates(scored)
        now = self._now()
        decisions: list[ScheduleDecision] = []

        for candidate in ranked:
            if len(decisions) >= limit:
                break
            if candidate.merge_pressure and policy.skip_on_merge_pressure:
                decision = self._build_decision(candidate, now=now, skipped=True)
                if persist:
                    err = self._persist_decision(decision, event_type="ScheduleSkipped")
                    if isinstance(err, Exception):
                        return err
                decisions.append(decision)
                continue
            decision = self._build_decision(candidate, now=now, skipped=False)
            if persist:
                err = self._persist_decision(decision, event_type="ScheduleDecision")
                if isinstance(err, Exception):
                    return err
            decisions.append(decision)
        return decisions

    def status(self, *, recent: int = 10) -> ScheduleStatus | Exception:
        policy = self.store.load_policy()
        if isinstance(policy, Exception):
            return policy
        ready = self._ready(None)
        if isinstance(ready, Exception):
            return ready
        decisions = self.store.list_decisions(limit=recent)
        if isinstance(decisions, Exception):
            return decisions
        depths = self._merge_depths()
        if isinstance(depths, Exception):
            return depths
        return ScheduleStatus(
            policy=policy,
            ready_count=len(ready),
            recent_decisions=list(reversed(decisions)),
            merge_pressure=depths,
        )

    def _ready(self, graph_id: str | None) -> list[TaskNode] | Exception:
        if self._ready_fn is not None:
            return self._ready_fn(graph_id)
        return self._tasks.ready(graph_id)

    def _warm_repos(self) -> set[str] | Exception:
        if self._worktrees_fn is None:
            try:
                from metagit.core.coordination.worktree_service import WorktreeService

                result = WorktreeService(self._session_root).list(status="active")
                if isinstance(result, Exception):
                    return set()
                return {row.repository for row in result.worktrees if row.repository}
            except Exception:  # noqa: BLE001 — affinity is optional
                return set()
        rows = self._worktrees_fn()
        if isinstance(rows, Exception):
            return rows
        warm: set[str] = set()
        for row in rows:
            repo = getattr(row, "repository", None)
            status = getattr(row, "status", "active")
            if isinstance(repo, str) and repo.strip() and status == "active":
                warm.add(repo.strip())
            elif isinstance(row, dict):
                repo_s = str(row.get("repository") or "").strip()
                if repo_s and str(row.get("status") or "active") == "active":
                    warm.add(repo_s)
        return warm

    def _merge_depths(self) -> dict[str, int] | Exception:
        if self._merge_status_fn is None:
            try:
                from metagit.core.merge.service import MergeOrchestrator

                rows = MergeOrchestrator(self._session_root).status()
                if isinstance(rows, Exception):
                    return {}
                return self._count_merge_pressure(rows)
            except Exception:  # noqa: BLE001 — merge is optional
                return {}
        rows = self._merge_status_fn()
        if isinstance(rows, Exception):
            return rows
        return self._count_merge_pressure(rows)

    def _count_merge_pressure(self, rows: list[Any]) -> dict[str, int]:
        counts: Counter[str] = Counter()
        for row in rows:
            status = getattr(row, "status", None)
            repo = getattr(row, "repository", None)
            if isinstance(row, dict):
                status = row.get("status")
                repo = row.get("repository")
            if status not in {"queued", "running"}:
                continue
            if isinstance(repo, str) and repo.strip():
                counts[repo.strip()] += 1
        return dict(counts)

    def _underrepresented_repos(
        self,
        ready: list[TaskNode],
        policy: SchedulePolicy,
    ) -> set[str] | Exception:
        if policy.weights.fairness <= 0 and not any(
            (override.fairness or 0) > 0 for override in policy.graph_overrides.values()
        ):
            return set()
        decisions = self.store.list_decisions()
        if isinstance(decisions, Exception):
            return decisions
        recent_repos = Counter()
        for decision in decisions:
            hints = decision.dispatch_hints or {}
            repo = hints.get("repository")
            if isinstance(repo, str) and repo.strip():
                recent_repos[repo.strip()] += 1
        ready_repos = {node.repository.strip() for node in ready if node.repository}
        if not ready_repos:
            return set()
        min_count = min(recent_repos.get(repo, 0) for repo in ready_repos)
        return {repo for repo in ready_repos if recent_repos.get(repo, 0) == min_count}

    def _build_decision(
        self,
        candidate: Any,
        *,
        now: str,
        skipped: bool,
    ) -> ScheduleDecision:
        node = candidate.node
        acl_commands: list[str] = []
        if node.acl is not None:
            acl_commands = list(node.acl.acl_commands)
        compile_command = None
        if node.project and node.repository:
            repo_name = node.repository.split("/")[-1]
            compile_command = (
                f"metagit context compile --project {node.project} --repo {repo_name} --task-id {node.node_id}"
            )
        reasons = list(candidate.reasons)
        if skipped:
            reasons.append("skipped_due_to_merge_pressure")
        return ScheduleDecision(
            decision_id=uuid.uuid4().hex,
            at=now,
            graph_id=node.graph_id,
            node_id=node.node_id,
            score=candidate.score,
            reasons=reasons,
            dispatch_hints={
                "title": node.title,
                "project": node.project,
                "repository": node.repository,
                "agent_id": node.agent_id,
                "priority": node.priority,
            },
            acl_commands=acl_commands,
            compile_command=compile_command,
            skipped=skipped,
        )

    def _persist_decision(
        self,
        decision: ScheduleDecision,
        *,
        event_type: str,
    ) -> None | Exception:
        saved = self.store.append_decision(decision)
        if isinstance(saved, Exception):
            return saved
        event = self._events.append(
            event_type,  # type: ignore[arg-type]
            {
                "decision_id": decision.decision_id,
                "graph_id": decision.graph_id,
                "node_id": decision.node_id,
                "score": decision.score,
                "skipped": decision.skipped,
                "reasons": decision.reasons,
            },
            at=decision.at,
        )
        if isinstance(event, Exception):
            return event
        return None


__all__ = ["SchedulerService"]

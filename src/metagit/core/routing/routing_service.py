#!/usr/bin/env python
"""Routing orchestration service for class catalog, run ledger, and promotion eval."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from metagit.core.config.models import MetagitConfig, RoutingConfig
from metagit.core.routing.class_store import ClassStore
from metagit.core.routing.models import Outcome, RequestClass, Run, RunDispatch, Tier
from metagit.core.routing.promotion import evaluate
from metagit.core.routing.router import MatchResult, rank_classes
from metagit.core.routing.run_store import RunStore, open_run_for
from metagit.core.state.retry import with_state_retry

_MISSING_ROUTING_MSG = "no routing.catalog configured - add a routing: block to .metagit.yml"


def _utc_now_iso(now_fn: Callable[[], datetime] | None = None) -> str:
    now = now_fn() if now_fn is not None else datetime.now(timezone.utc)
    return now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _require_routing_config(config: MetagitConfig) -> RoutingConfig:
    routing = config.routing
    if routing is None or not routing.catalog.strip() or not routing.runs.strip():
        raise ValueError(_MISSING_ROUTING_MSG)
    return routing


class RoutingService:
    """Orchestrates deterministic query, run ledger lifecycle, and promotion evaluation."""

    def __init__(
        self,
        config: MetagitConfig,
        *,
        workspace_root: str,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._routing = _require_routing_config(config)
        self._workspace_root = Path(workspace_root).expanduser().resolve()
        self._now_fn = now_fn
        self.class_store = ClassStore(self._workspace_root / self._routing.catalog)
        self.run_store = RunStore(self._workspace_root / self._routing.runs)

    def query(self, ask: str, *, limit: int = 5) -> list[MatchResult]:
        classes = self.class_store.list()
        return rank_classes(classes, ask, limit=limit)

    def list_classes(self, *, tier: Optional[Tier] = None, ready: bool = False) -> list[RequestClass]:
        rows = self.class_store.list()
        if tier is not None:
            rows = [row for row in rows if row.tier == tier]
        if ready:
            rows = [row for row in rows if row.promotion_state == "ready-needs-executor"]
        rows.sort(key=lambda row: row.id)
        return rows

    def show_class(self, class_id: str) -> dict[str, object]:
        row, _ = self.class_store.load(class_id)
        if row is None:
            raise ValueError(f"class not found: {class_id}")
        runs = self.run_store.list_for_class(class_id)
        runs.sort(key=lambda item: item.id)
        return {
            "class": row,
            "runs": runs,
            "run_count": len(runs),
        }

    def open_run(
        self,
        *,
        class_id: str,
        actor: str,
        tier: Optional[Tier] = None,
        lane: Optional[str] = None,
        objective: Optional[str] = None,
        session_id: Optional[str] = None,
        branch: Optional[str] = None,
        workdir: Optional[str] = None,
        doctrine_chars: Optional[int] = None,
    ) -> Run:
        cls, _ = self.class_store.load(class_id)
        if cls is None:
            raise ValueError(f"class not found: {class_id}")

        dispatch = RunDispatch(
            session_id=session_id,
            branch=branch,
            workdir=workdir,
            doctrine_chars=doctrine_chars,
        )
        run = open_run_for(
            class_id,
            tier=tier or cls.tier,
            actor=actor,
            lane=lane if lane is not None else cls.lane,
            objective=objective,
            dispatch=dispatch,
            now_fn=self._now_fn,
        )

        def _save() -> Run:
            self.run_store.save(run, expected=None)
            return run

        return with_state_retry(_save)

    def close_run(
        self,
        *,
        run_id: str,
        outcome: Outcome,
        mr_url: Optional[str] = None,
        gates: Optional[list[str]] = None,
        evidence_file: Optional[str] = None,
    ) -> Run:
        def _close() -> Run:
            run, token = self.run_store.load(run_id)
            if run is None:
                raise ValueError(f"run not found: {run_id}")
            if run.closed is not None or run.outcome is not None:
                raise ValueError(f"run is already closed: {run_id}")

            updated = run.model_copy(deep=True)
            updated.outcome = outcome
            updated.closed = _utc_now_iso(self._now_fn)
            if mr_url:
                updated.artifact.mr_url = mr_url
            if gates:
                updated.evidence.gates_run.extend(gates)
            if evidence_file:
                updated.evidence.digest = evidence_file

            self.run_store.save(updated, expected=token)
            return updated

        return with_state_retry(_close)

    def list_runs(
        self,
        *,
        class_id: Optional[str] = None,
        outcome: Optional[Outcome] = None,
        open_only: bool = False,
    ) -> list[Run]:
        rows = self.run_store.list()
        if class_id is not None:
            rows = [row for row in rows if row.cls == class_id]
        if outcome is not None:
            rows = [row for row in rows if row.outcome == outcome]
        if open_only:
            rows = [row for row in rows if row.outcome is None]
        rows.sort(key=lambda row: row.id)
        return rows

    def evaluate(self, *, class_id: Optional[str] = None, dry_run: bool = False) -> list[RequestClass]:
        rows = [self._load_class_or_fail(class_id)] if class_id is not None else self.class_store.list()

        policy = self._routing.policy
        updated_rows: list[RequestClass] = []
        for row in rows:
            runs = self.run_store.list_for_class(row.id)
            tier, state, evidence = evaluate(row, runs, policy)
            candidate = row.model_copy(deep=True)
            candidate.tier = tier
            candidate.promotion_state = state
            candidate.evidence = evidence
            candidate.updated = _utc_now_iso(self._now_fn)

            if not dry_run:
                self._save_class(candidate)
            updated_rows.append(candidate)
        updated_rows.sort(key=lambda item: item.id)
        return updated_rows

    def _load_class_or_fail(self, class_id: str) -> RequestClass:
        row, _ = self.class_store.load(class_id)
        if row is None:
            raise ValueError(f"class not found: {class_id}")
        return row

    def _save_class(self, row: RequestClass) -> None:
        def _save() -> None:
            _current, token = self.class_store.load(row.id)
            self.class_store.save(row, expected=token)

        with_state_retry(_save)


__all__ = ["RoutingService"]

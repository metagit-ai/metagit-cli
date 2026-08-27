#!/usr/bin/env python
"""Simulated multi-agent helpers (no model runtime)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any, TypeVar

from metagit.core.aos.models import AosNextResult
from metagit.core.coordination.models import ClaimCheckResult, FileClaim, Lease

from .workspace import ScenarioWorkspace

T = TypeVar("T")


class SimulatedAgent:
    """Minimal agent façade over real coordination services."""

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id

    def allocate_and_lease(
        self,
        ws: ScenarioWorkspace,
        *,
        task_id: str,
        repository: str | None = None,
        ttl: str = "60",
        branch: str | None = None,
    ) -> Lease | Exception:
        repo = repository or ws.default_repository
        branches = ws.branch_service()
        leases = ws.lease_service()
        if branch is None:
            allocation = branches.allocate(
                repository=repo,
                agent_id=self.agent_id,
                task_id=task_id,
            )
            if isinstance(allocation, Exception):
                return allocation
            branch_name = allocation.name
        else:
            branch_name = branch
        return leases.acquire(
            repository=repo,
            agent_id=self.agent_id,
            task_id=task_id,
            branch=branch_name,
            ttl=ttl,
        )

    def declare_claim(
        self,
        ws: ScenarioWorkspace,
        *,
        patterns: list[str],
        repository: str | None = None,
        allow_conflicts: bool = True,
    ) -> FileClaim | ClaimCheckResult | Exception:
        return ws.claim_service().declare(
            repository=repository or ws.default_repository,
            agent_id=self.agent_id,
            patterns=patterns,
            allow_conflicts=allow_conflicts,
        )

    def check_claim(
        self,
        ws: ScenarioWorkspace,
        *,
        patterns: list[str],
        repository: str | None = None,
    ) -> ClaimCheckResult | Exception:
        return ws.claim_service().check(
            repository=repository or ws.default_repository,
            patterns=patterns,
            agent_id=self.agent_id,
        )

    def aos_next(
        self,
        ws: ScenarioWorkspace,
        *,
        commit: bool = False,
        apply_hints: bool = False,
        graph_id: str | None = None,
        limit: int = 1,
    ) -> AosNextResult | Exception:
        return ws.aos().next(
            commit=commit,
            apply_hints=apply_hints,
            agent_id=self.agent_id,
            graph_id=graph_id,
            limit=limit,
        )

    def complete_task(
        self,
        ws: ScenarioWorkspace,
        *,
        node_id: str,
        graph_id: str | None = None,
    ) -> Any:
        return ws.task_graph().complete(node_id, graph_id=graph_id)


class AgentPool:
    """Start N agent actions at a Barrier and collect results by agent_id order."""

    def __init__(self, agent_ids: list[str]) -> None:
        self.agents = [SimulatedAgent(agent_id) for agent_id in agent_ids]

    def run_barrier(
        self,
        actions: list[Callable[[SimulatedAgent], T]],
        *,
        timeout: float = 10.0,
    ) -> list[T | BaseException]:
        if len(actions) != len(self.agents):
            raise ValueError("actions length must match agent count")
        barrier = threading.Barrier(len(self.agents))
        results: list[T | BaseException | None] = [None] * len(self.agents)
        errors: list[BaseException] = []

        def _run(index: int) -> None:
            agent = self.agents[index]
            try:
                barrier.wait(timeout=timeout)
                results[index] = actions[index](agent)
            except BaseException as exc:  # noqa: BLE001 — collect for deterministic return
                results[index] = exc
                errors.append(exc)

        threads = [
            threading.Thread(target=_run, args=(idx,), name=f"scenario-agent-{agent.agent_id}")
            for idx, agent in enumerate(self.agents)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=timeout + 2.0)
        hung = [thread.name for thread in threads if thread.is_alive()]
        if hung:
            raise TimeoutError(f"scenario agent threads hung: {hung}")
        return [row if row is not None else RuntimeError("missing result") for row in results]

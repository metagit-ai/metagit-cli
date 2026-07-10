#!/usr/bin/env python
"""Unit tests for deterministic scheduler scoring."""

from __future__ import annotations

from metagit.core.scheduler.models import SchedulePolicy, ScheduleWeights
from metagit.core.scheduler.scoring import rank_candidates, score_node
from metagit.core.taskgraph.models import TaskNode


def _node(
    node_id: str,
    *,
    priority: int = 0,
    repository: str | None = "project/a",
    estimated_tokens: int | None = None,
    context_budget: int | None = None,
) -> TaskNode:
    return TaskNode(
        node_id=node_id,
        graph_id="g1",
        title=node_id,
        status="ready",
        repository=repository,
        priority=priority,
        estimated_tokens=estimated_tokens,
        context_budget=context_budget,
        created_at="2026-07-09T00:00:00Z",
        updated_at="2026-07-09T00:00:00Z",
    )


def test_higher_priority_wins_when_other_factors_equal() -> None:
    policy = SchedulePolicy(weights=ScheduleWeights(affinity=0.0, cost=0.0))
    low = score_node(_node("a", priority=1), policy=policy)
    high = score_node(_node("b", priority=5), policy=policy)
    ranked = rank_candidates([low, high])
    assert ranked[0].node.node_id == "b"
    assert ranked[0].score > ranked[1].score


def test_affinity_boosts_warm_worktree_repo() -> None:
    policy = SchedulePolicy(weights=ScheduleWeights(priority=0.0, cost=0.0, affinity=1.0))
    cold = score_node(_node("cold", repository="project/cold"), policy=policy, warm_repos=set())
    warm = score_node(
        _node("warm", repository="project/warm"),
        policy=policy,
        warm_repos={"project/warm"},
    )
    ranked = rank_candidates([cold, warm])
    assert ranked[0].node.node_id == "warm"


def test_lower_estimated_tokens_scores_higher_on_cost_weight() -> None:
    policy = SchedulePolicy(weights=ScheduleWeights(priority=0.0, affinity=0.0, cost=1.0))
    expensive = score_node(_node("exp", estimated_tokens=4000), policy=policy)
    cheap = score_node(_node("cheap", estimated_tokens=100), policy=policy)
    ranked = rank_candidates([expensive, cheap])
    assert ranked[0].node.node_id == "cheap"


def test_tie_break_by_node_id_when_scores_equal() -> None:
    policy = SchedulePolicy(weights=ScheduleWeights(priority=0.0, affinity=0.0, cost=0.0))
    first = score_node(_node("z-node"), policy=policy)
    second = score_node(_node("a-node"), policy=policy)
    ranked = rank_candidates([first, second])
    assert [item.node.node_id for item in ranked] == ["a-node", "z-node"]

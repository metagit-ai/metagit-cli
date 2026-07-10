#!/usr/bin/env python
"""Pure deterministic scoring for ready task nodes (RFC-0012)."""

from __future__ import annotations

from dataclasses import dataclass

from metagit.core.scheduler.models import SchedulePolicy, ScheduleWeights
from metagit.core.taskgraph.models import TaskNode

DEFAULT_TOKENS = 1000


@dataclass(frozen=True)
class ScoredCandidate:
    """A ready node with computed score and human-readable reasons."""

    node: TaskNode
    score: float
    effective_tokens: int
    reasons: list[str]
    merge_pressure: bool = False


def effective_tokens(node: TaskNode) -> int:
    """Resolve token estimate: estimated_tokens → context_budget → default."""
    if node.estimated_tokens is not None and node.estimated_tokens >= 0:
        return int(node.estimated_tokens)
    if node.context_budget is not None and node.context_budget >= 0:
        return int(node.context_budget)
    return DEFAULT_TOKENS


def resolve_weights(policy: SchedulePolicy, graph_id: str) -> ScheduleWeights:
    """Merge workspace weights with optional per-graph overrides."""
    base = policy.weights
    override = policy.graph_overrides.get(graph_id)
    if override is None:
        return base
    return ScheduleWeights(
        priority=override.priority if override.priority is not None else base.priority,
        affinity=override.affinity if override.affinity is not None else base.affinity,
        cost=override.cost if override.cost is not None else base.cost,
        fairness=override.fairness if override.fairness is not None else base.fairness,
    )


def score_node(
    node: TaskNode,
    *,
    policy: SchedulePolicy,
    warm_repos: set[str] | None = None,
    underrepresented_repos: set[str] | None = None,
    merge_depth_by_repo: dict[str, int] | None = None,
) -> ScoredCandidate:
    """Score one ready node using policy weights and soft merge pressure."""
    weights = resolve_weights(policy, node.graph_id)
    warm = warm_repos or set()
    under = underrepresented_repos or set()
    depths = merge_depth_by_repo or {}
    tokens = effective_tokens(node)
    cost_score = 1.0 / (1.0 + (tokens / float(DEFAULT_TOKENS)))
    repo = (node.repository or "").strip()
    affinity = 1.0 if repo and repo in warm else 0.0
    fairness = 1.0 if weights.fairness > 0 and repo and repo in under else 0.0
    priority = float(node.priority)
    raw = (
        weights.priority * priority
        + weights.affinity * affinity
        + weights.cost * cost_score
        + weights.fairness * fairness
    )
    reasons = [
        f"priority={node.priority}",
        f"affinity={affinity:.0f}",
        f"cost={cost_score:.4f}(tokens={tokens})",
    ]
    if weights.fairness > 0:
        reasons.append(f"fairness={fairness:.0f}")

    depth = depths.get(repo, 0) if repo else 0
    under_pressure = bool(repo and depth >= policy.merge_queue_threshold)
    if under_pressure:
        raw -= policy.merge_pressure_penalty
        reasons.append(
            f"merge_pressure depth={depth} threshold={policy.merge_queue_threshold} "
            f"penalty={policy.merge_pressure_penalty}"
        )

    return ScoredCandidate(
        node=node,
        score=round(raw, 6),
        effective_tokens=tokens,
        reasons=reasons,
        merge_pressure=under_pressure,
    )


def rank_candidates(candidates: list[ScoredCandidate]) -> list[ScoredCandidate]:
    """Sort by score desc, effective tokens asc, node_id asc."""
    return sorted(
        candidates,
        key=lambda item: (-item.score, item.effective_tokens, item.node.node_id),
    )


__all__ = [
    "DEFAULT_TOKENS",
    "ScoredCandidate",
    "effective_tokens",
    "rank_candidates",
    "resolve_weights",
    "score_node",
]

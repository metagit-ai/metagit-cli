#!/usr/bin/env python
"""Pure tier-promotion evaluation for routing classes."""

from __future__ import annotations

from metagit.core.config.models import RoutingPolicy
from metagit.core.routing.models import ClassEvidence, RequestClass, Run, Tier

_TIERS: list[Tier] = ["deterministic", "skilled", "novel"]


def _up_one(tier: Tier, *, max_tier: Tier) -> Tier:
    current_idx = _TIERS.index(tier)
    ceiling_idx = _TIERS.index(max_tier)
    target_idx = max(current_idx - 1, ceiling_idx)
    return _TIERS[target_idx]


def _down_one(tier: Tier) -> Tier:
    current_idx = _TIERS.index(tier)
    target_idx = min(current_idx + 1, len(_TIERS) - 1)
    return _TIERS[target_idx]


def evaluate(cls: RequestClass, runs: list[Run], policy: RoutingPolicy) -> tuple[Tier, str, ClassEvidence]:
    """Return tier, promotion state, and evidence justified by run history."""
    max_tier: Tier = "skilled" if cls.mutates else "deterministic"
    tier: Tier = cls.tier
    state = "stable"

    closed = [row for row in runs if row.outcome is not None]
    ordered = sorted(closed, key=lambda row: row.id)

    streak = 0
    bad: str | None = None
    for row in reversed(ordered):
        if row.outcome == "abandoned":
            continue
        if row.outcome in policy.demote_on:
            bad = row.outcome
            break
        if row.outcome == "landed":
            streak += 1

    if bad is not None:
        tier = _down_one(tier)
        state = f"demoted:{bad}"
    elif streak >= policy.promote_after_clean:
        target = _up_one(tier, max_tier=max_tier)
        if target == "deterministic" and not cls.executor:
            state = "ready-needs-executor"
        else:
            tier = target

    landed = sum(1 for row in ordered if row.outcome == "landed")
    bounced = sum(1 for row in ordered if row.outcome == "bounced")
    noop = sum(1 for row in ordered if row.outcome == "noop")
    last_run = None
    if ordered:
        last_run = ordered[-1].closed or ordered[-1].opened

    failure_modes: list[str] = []
    if bounced:
        failure_modes.append("bounced")
    if noop:
        failure_modes.append("noop")

    evidence = ClassEvidence(
        runs_landed=landed,
        runs_bounced=bounced,
        runs_noop=noop,
        clean_streak=streak,
        last_run=last_run,
        failure_modes=failure_modes,
    )
    return tier, state, evidence


__all__ = ["evaluate"]

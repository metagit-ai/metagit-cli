#!/usr/bin/env python
"""Declarative mutation policy evaluation (RFC-0022 MVP)."""

from __future__ import annotations

import os
from typing import Literal, Optional

from pydantic import BaseModel, Field

ActionClass = Literal[
    "sync",
    "merge_integrate",
    "claim_declare",
    "claim_release",
    "catalog_edit",
    "remote_state_write",
    "acl_bind",
    "aos_recover",
    "run_open",
]

Decision = Literal["allow", "deny"]

_HIGH_RISK: set[str] = {
    "merge_integrate",
    "catalog_edit",
    "remote_state_write",
    "claim_release",
}


class PolicyRule(BaseModel):
    action: ActionClass
    effect: Decision = "allow"
    reason: Optional[str] = None


class MutationPolicy(BaseModel):
    """Optional AppConfig / manifest policy for mutating action classes."""

    default_effect: Decision = "allow"
    agent_mode_high_risk_default: Decision = "deny"
    rules: list[PolicyRule] = Field(default_factory=list)


class PolicyDecision(BaseModel):
    action: ActionClass
    effect: Decision
    reason: str
    agent_mode: bool
    matched_rule: bool = False


def is_agent_mode(env: Optional[dict[str, str]] = None) -> bool:
    source = env if env is not None else os.environ
    value = str(source.get("METAGIT_AGENT_MODE", "")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def evaluate_action(
    action: ActionClass,
    policy: MutationPolicy | None = None,
    *,
    env: Optional[dict[str, str]] = None,
) -> PolicyDecision:
    """Deterministically evaluate whether an action class is allowed."""
    cfg = policy or MutationPolicy()
    agent = is_agent_mode(env)
    for rule in cfg.rules:
        if rule.action == action:
            return PolicyDecision(
                action=action,
                effect=rule.effect,
                reason=rule.reason or f"matched rule for {action}",
                agent_mode=agent,
                matched_rule=True,
            )
    if agent and action in _HIGH_RISK:
        return PolicyDecision(
            action=action,
            effect=cfg.agent_mode_high_risk_default,
            reason="agent_mode high-risk default",
            agent_mode=agent,
            matched_rule=False,
        )
    return PolicyDecision(
        action=action,
        effect=cfg.default_effect,
        reason="policy default_effect",
        agent_mode=agent,
        matched_rule=False,
    )


__all__ = [
    "ActionClass",
    "Decision",
    "MutationPolicy",
    "PolicyDecision",
    "PolicyRule",
    "evaluate_action",
    "is_agent_mode",
]

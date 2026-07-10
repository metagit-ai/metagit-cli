#!/usr/bin/env python
"""Pydantic models for the Distributed Agent Scheduler (RFC-0012)."""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

_ID_PATTERN = re.compile(r"^[\w.-]+$")

ScheduleEventType = Literal["ScheduleDecision", "ScheduleSkipped"]


def _validate_id(value: str, *, label: str) -> str:
    stripped = value.strip()
    if not stripped or not _ID_PATTERN.match(stripped):
        raise ValueError(f"{label} must match slug pattern [alphanumeric, underscore, dot, hyphen]")
    return stripped


class ScheduleWeights(BaseModel):
    """Relative weights for scoring factors."""

    priority: float = 1.0
    affinity: float = 0.5
    cost: float = 0.25
    fairness: float = 0.0


class ScheduleWeightOverrides(BaseModel):
    """Optional per-graph weight overrides (partial)."""

    priority: Optional[float] = None
    affinity: Optional[float] = None
    cost: Optional[float] = None
    fairness: Optional[float] = None


class SchedulePolicy(BaseModel):
    """Workspace schedule policy persisted as ``policy.json``."""

    weights: ScheduleWeights = Field(default_factory=ScheduleWeights)
    merge_queue_threshold: int = 3
    merge_pressure_penalty: float = 2.0
    skip_on_merge_pressure: bool = False
    graph_overrides: dict[str, ScheduleWeightOverrides] = Field(default_factory=dict)

    @field_validator("merge_queue_threshold")
    @classmethod
    def validate_threshold(cls, value: int) -> int:
        if value < 1:
            raise ValueError("merge_queue_threshold must be >= 1")
        return value


class ScheduleDecision(BaseModel):
    """One schedule decision (or skipped decision) for a ready node."""

    decision_id: str
    at: str
    graph_id: str
    node_id: str
    score: float
    reasons: list[str] = Field(default_factory=list)
    dispatch_hints: dict[str, Any] = Field(default_factory=dict)
    acl_commands: list[str] = Field(default_factory=list)
    compile_command: Optional[str] = None
    skipped: bool = False

    @field_validator("decision_id", "graph_id", "node_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        return _validate_id(value, label="id")


class ScheduleStatus(BaseModel):
    """Operator-facing scheduler status envelope."""

    policy: SchedulePolicy
    ready_count: int = 0
    recent_decisions: list[ScheduleDecision] = Field(default_factory=list)
    merge_pressure: dict[str, int] = Field(default_factory=dict)


class ScheduleEvent(BaseModel):
    """Typed scheduler lifecycle event."""

    event_id: str
    type: ScheduleEventType
    at: str
    payload: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "ScheduleDecision",
    "ScheduleEvent",
    "ScheduleEventType",
    "SchedulePolicy",
    "ScheduleStatus",
    "ScheduleWeightOverrides",
    "ScheduleWeights",
]

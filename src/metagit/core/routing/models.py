#!/usr/bin/env python
"""Pydantic models for request routing classes and execution runs."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Tier = Literal["deterministic", "skilled", "novel"]
Outcome = Literal["landed", "bounced", "noop", "abandoned"]


class ClassEvidence(BaseModel):
    """Derived roll-up of a class's run history."""

    runs_landed: int = 0
    runs_bounced: int = 0
    runs_noop: int = 0
    clean_streak: int = 0
    last_run: Optional[str] = None
    failure_modes: list[str] = Field(default_factory=list)


class RequestClass(BaseModel):
    """A recurring kind of request: the intent to action mapping."""

    id: str
    title: str
    triggers: list[str] = Field(default_factory=list, max_length=12)
    skill: Optional[str] = None
    lane: Optional[str] = None
    artifact: Optional[str] = None
    gates: list[str] = Field(default_factory=list)
    tier: Tier = "novel"
    mutates: bool = True
    executor: Optional[str] = None
    promotion_state: str = "stable"
    evidence: Optional[ClassEvidence] = None
    notes: Optional[str] = None
    updated: Optional[str] = None


class RunDispatch(BaseModel):
    session_id: Optional[str] = None
    branch: Optional[str] = None
    workdir: Optional[str] = None
    doctrine_chars: Optional[int] = None


class RunEvidence(BaseModel):
    gates_run: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    steering_turns: Optional[int] = None
    digest: Optional[str] = None


class RunArtifact(BaseModel):
    mr_url: Optional[str] = None
    merged_at: Optional[str] = None


class Run(BaseModel):
    """One execution of a class. Outcome None means still open."""

    id: str
    cls: str = Field(alias="class")
    tier: Tier
    lane: Optional[str] = None
    actor: str
    objective: Optional[str] = None
    dispatch: RunDispatch = Field(default_factory=RunDispatch)
    outcome: Optional[Outcome] = None
    artifact: RunArtifact = Field(default_factory=RunArtifact)
    evidence: RunEvidence = Field(default_factory=RunEvidence)
    opened: str
    closed: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


__all__ = [
    "ClassEvidence",
    "Outcome",
    "RequestClass",
    "Run",
    "RunArtifact",
    "RunDispatch",
    "RunEvidence",
    "Tier",
]

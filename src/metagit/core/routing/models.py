#!/usr/bin/env python
"""Pydantic models for request routing classes and execution runs."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Tier = Literal["deterministic", "skilled", "novel"]
Outcome = Literal["landed", "bounced", "noop", "abandoned"]
ExpectedOutputKind = Literal["pull_request", "merge_request", "patch", "report", "none"]


class CapabilitySelector(BaseModel):
    """Deterministic topology selector for capability-scoped request classes."""

    project_types: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict)
    path_globs: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    model_config = ConfigDict(extra="forbid")


class CapabilityStep(BaseModel):
    """Advisory workflow step for a capability contract."""

    name: str
    description: Optional[str] = None
    command: Optional[str] = None
    gate: bool = False
    model_config = ConfigDict(extra="forbid")


class CapabilityScope(BaseModel):
    """Advisory read/write boundary declared by capability config."""

    allowed_paths: list[str] = Field(default_factory=lambda: ["**"])
    writable_paths: list[str] = Field(default_factory=list)
    forbidden_paths: list[str] = Field(default_factory=list)
    model_config = ConfigDict(extra="forbid")


class CapabilitySpec(BaseModel):
    """Capability metadata attached to one request class."""

    selector: CapabilitySelector = Field(default_factory=CapabilitySelector)
    scope: CapabilityScope = Field(default_factory=CapabilityScope)
    workflow: list[CapabilityStep] = Field(default_factory=list)
    expected_output: ExpectedOutputKind = "none"
    required_tools: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    model_config = ConfigDict(extra="forbid")


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
    capability: Optional[CapabilitySpec] = None


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
    "CapabilityScope",
    "CapabilitySelector",
    "CapabilitySpec",
    "CapabilityStep",
    "ClassEvidence",
    "ExpectedOutputKind",
    "Outcome",
    "RequestClass",
    "Run",
    "RunArtifact",
    "RunDispatch",
    "RunEvidence",
    "Tier",
]

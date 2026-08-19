#!/usr/bin/env python
"""Pydantic envelopes for capability resolve and compile flows."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from metagit.core.routing.models import CapabilityStep, ExpectedOutputKind


class CapabilityRepoRef(BaseModel):
    project: str
    repo: str
    path: Optional[str] = None
    url: Optional[str] = None
    allowed_paths: list[str] = Field(default_factory=list)
    writable_paths: list[str] = Field(default_factory=list)


class CapabilityMatch(BaseModel):
    capability_id: str
    confidence: float
    why: str
    selector_ok: bool


class CapabilityEnvelope(BaseModel):
    """Task-scoped capability contract for orchestrator consumers."""

    ok: bool = True
    schema_version: str = "1.0"
    capability_id: str
    title: str
    project: str
    repository: CapabilityRepoRef
    cwd: str
    allowed_paths: list[str] = Field(default_factory=list)
    writable_paths: list[str] = Field(default_factory=list)
    instructions: str
    instruction_layers: list[dict] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    mcp: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    workflow: list[CapabilityStep] = Field(default_factory=list)
    gates: list[str] = Field(default_factory=list)
    expected_output: ExpectedOutputKind = "none"
    context_artifact_path: Optional[str] = None
    tier: str = "novel"
    executor: Optional[str] = None
    task_id: Optional[str] = None
    objective_id: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    generated_at: str
    source: Literal["metagit"] = "metagit"

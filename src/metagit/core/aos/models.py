#!/usr/bin/env python
"""Pydantic envelopes for AOS composition (RFC-0013)."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

FindingSeverity = Literal["info", "warning", "error"]


class AosSubsystemSection(BaseModel):
    """One subsystem slice in an AOS status snapshot."""

    available: bool
    summary: dict[str, Any] = Field(default_factory=dict)


class AosStatusResult(BaseModel):
    """Read-only aggregation of coordination subsystem status."""

    generated_at: str
    subsystems: dict[str, AosSubsystemSection] = Field(default_factory=dict)


class AosFinding(BaseModel):
    """A single doctor finding."""

    severity: FindingSeverity
    code: str
    message: str
    subsystem: str
    affected_ids: list[str] = Field(default_factory=list)


class AosRecoveryRecipe(BaseModel):
    """Actionable recovery recipe attached to doctor output."""

    code: str
    action: str
    description: str
    command: str
    safe_default: bool = True
    requires_flag: Optional[str] = None
    subsystem: str


class AosDoctorResult(AosStatusResult):
    """Status plus findings, suggested commands, and optional fix results."""

    findings: list[AosFinding] = Field(default_factory=list)
    suggested_commands: list[str] = Field(default_factory=list)
    fixed: list[str] = Field(default_factory=list)
    recovery_recipes: list[AosRecoveryRecipe] = Field(default_factory=list)


class AosRecoverResult(BaseModel):
    """Outcome of a gated aos recover invocation."""

    generated_at: str
    agent_id: str
    actions: list[str] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class AosHeartbeatResult(BaseModel):
    """Outcome of lease renewal heartbeat."""

    generated_at: str
    agent_id: str
    renewed: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class AosNextResult(BaseModel):
    """Composed 'what to do next' envelope (preview or committed)."""

    generated_at: str
    decision: Optional[dict[str, Any]] = None
    compile_command: Optional[str] = None
    acl_commands: list[str] = Field(default_factory=list)
    committed: bool = False
    hints_applied: bool = False
    scheduler_available: bool = False
    reasons: list[str] = Field(default_factory=list)
    run_id: Optional[str] = None


__all__ = [
    "AosDoctorResult",
    "AosFinding",
    "AosHeartbeatResult",
    "AosNextResult",
    "AosRecoverResult",
    "AosRecoveryRecipe",
    "AosStatusResult",
    "AosSubsystemSection",
    "FindingSeverity",
]

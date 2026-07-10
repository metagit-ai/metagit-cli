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


class AosDoctorResult(AosStatusResult):
    """Status plus findings, suggested commands, and optional fix results."""

    findings: list[AosFinding] = Field(default_factory=list)
    suggested_commands: list[str] = Field(default_factory=list)
    fixed: list[str] = Field(default_factory=list)


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


__all__ = [
    "AosDoctorResult",
    "AosFinding",
    "AosNextResult",
    "AosStatusResult",
    "AosSubsystemSection",
    "FindingSeverity",
]

#!/usr/bin/env python
"""Tests for AOS composition models."""

from metagit.core.aos.models import (
    AosDoctorResult,
    AosFinding,
    AosNextResult,
    AosStatusResult,
    AosSubsystemSection,
)


def test_subsystem_section_defaults() -> None:
    section = AosSubsystemSection(available=False)
    assert section.available is False
    assert section.summary == {}


def test_status_result_requires_generated_at() -> None:
    result = AosStatusResult(
        generated_at="2026-07-09T00:00:00Z",
        subsystems={
            "acl": AosSubsystemSection(available=True, summary={"leases_active": 0}),
            "taskgraph": AosSubsystemSection(available=True, summary={"ready": 0}),
        },
    )
    assert "acl" in result.subsystems
    assert result.subsystems["taskgraph"].available is True


def test_doctor_finding_and_next_flags() -> None:
    finding = AosFinding(
        severity="warning",
        code="stale_lease",
        message="lease expired",
        subsystem="acl",
    )
    doctor = AosDoctorResult(
        generated_at="2026-07-09T00:00:00Z",
        subsystems={},
        findings=[finding],
        suggested_commands=["metagit worktree gc"],
        fixed=[],
    )
    assert doctor.findings[0].code == "stale_lease"
    nxt = AosNextResult(
        generated_at="2026-07-09T00:00:00Z",
        committed=False,
        hints_applied=False,
        scheduler_available=True,
    )
    assert nxt.decision is None
    assert nxt.acl_commands == []

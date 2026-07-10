#!/usr/bin/env python
"""AosService.status aggregation and degrade behavior."""

from metagit.core.aos.models import AosSubsystemSection
from metagit.core.aos.service import AosService


class FakeCollectors:
    def __init__(self, sections: dict[str, AosSubsystemSection]) -> None:
        self._sections = sections

    def collect_all(self) -> dict[str, AosSubsystemSection]:
        return self._sections


def test_status_includes_only_provided_sections(tmp_path) -> None:
    sections = {
        "acl": AosSubsystemSection(available=True, summary={"leases_active": 1}),
        "taskgraph": AosSubsystemSection(available=True, summary={"ready": 2, "blocked": 1}),
        "scheduler": AosSubsystemSection(available=False),
    }
    svc = AosService(str(tmp_path), collectors=FakeCollectors(sections))
    result = svc.status()
    assert not isinstance(result, Exception)
    assert result.subsystems["acl"].summary["leases_active"] == 1
    assert result.subsystems["scheduler"].available is False


def test_status_works_with_acl_and_taskgraph_only(tmp_path) -> None:
    sections = {
        "acl": AosSubsystemSection(available=True, summary={}),
        "taskgraph": AosSubsystemSection(available=True, summary={"ready": 0}),
        "context_compile": AosSubsystemSection(available=False),
        "semantic": AosSubsystemSection(available=False),
        "merge": AosSubsystemSection(available=False),
        "scheduler": AosSubsystemSection(available=False),
    }
    svc = AosService(str(tmp_path), collectors=FakeCollectors(sections))
    result = svc.status()
    assert not isinstance(result, Exception)
    assert result.subsystems["taskgraph"].available is True

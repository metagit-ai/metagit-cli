#!/usr/bin/env python
"""Doctor findings and --fix gating."""

from metagit.core.aos.models import AosSubsystemSection
from metagit.core.aos.service import AosService


class FakeCollectors:
    def __init__(self) -> None:
        self.sections = {
            "acl": AosSubsystemSection(
                available=True,
                summary={"leases_expired": 1, "worktrees_active": 1},
            ),
            "taskgraph": AosSubsystemSection(
                available=True,
                summary={"ready": 0, "blocked": 2},
            ),
            "scheduler": AosSubsystemSection(available=False),
            "context_compile": AosSubsystemSection(available=False),
            "semantic": AosSubsystemSection(available=False),
            "merge": AosSubsystemSection(available=False),
        }

    def collect_all(self):
        return self.sections


def test_doctor_report_only_suggests_commands(tmp_path) -> None:
    svc = AosService(str(tmp_path), collectors=FakeCollectors())
    result = svc.doctor(fix=False, confirm=False)
    assert not isinstance(result, Exception)
    assert result.fixed == []
    assert any(f.code == "blocked_tasks" for f in result.findings)
    assert any("worktree gc" in c or "lease" in c for c in result.suggested_commands)


def test_doctor_fix_without_confirm_errors(tmp_path) -> None:
    svc = AosService(str(tmp_path), collectors=FakeCollectors())
    result = svc.doctor(fix=True, confirm=False)
    assert isinstance(result, Exception)


def test_doctor_fix_with_confirm_calls_gc(tmp_path) -> None:
    calls: list[str] = []

    def fake_fix(_svc: AosService) -> list[str]:
        calls.append("gc")
        return ["destroyed:wt-1"]

    svc = AosService(str(tmp_path), collectors=FakeCollectors(), fix_fn=fake_fix)
    result = svc.doctor(fix=True, confirm=True)
    assert not isinstance(result, Exception)
    assert calls == ["gc"]
    assert result.fixed

#!/usr/bin/env python
"""AosService.next preview, commit, and apply-hints."""

from metagit.core.aos.service import AosService
from metagit.core.scheduler.models import ScheduleDecision


def test_next_preview_does_not_commit(tmp_path) -> None:
    decisions = [
        ScheduleDecision(
            decision_id="d1",
            at="2026-07-09T00:00:00Z",
            graph_id="g1",
            node_id="n1",
            score=1.0,
            acl_commands=["metagit lease acquire --allocate"],
            compile_command="metagit context compile --project p --repo r --task-id n1",
        )
    ]

    class Sched:
        def preview_next(self, graph_id=None, *, limit=1):
            return decisions

        def next(self, graph_id=None, *, limit=1):
            raise AssertionError("next must not be called in preview")

    svc = AosService(str(tmp_path), scheduler=Sched())
    result = svc.next(commit=False, apply_hints=False)
    assert not isinstance(result, Exception)
    assert result.committed is False
    assert result.scheduler_available is True
    assert result.compile_command is not None
    assert result.hints_applied is False


def test_next_commit_delegates_to_scheduler_next(tmp_path) -> None:
    class Sched:
        def preview_next(self, graph_id=None, *, limit=1):
            raise AssertionError("preview must not be used when commit=True")

        def next(self, graph_id=None, *, limit=1):
            return [
                ScheduleDecision(
                    decision_id="d2",
                    at="2026-07-09T00:00:00Z",
                    graph_id="g1",
                    node_id="n1",
                    score=2.0,
                )
            ]

    svc = AosService(str(tmp_path), scheduler=Sched())
    result = svc.next(commit=True)
    assert not isinstance(result, Exception)
    assert result.committed is True
    assert result.decision is not None


def test_apply_hints_requires_agent_id(tmp_path) -> None:
    class Sched:
        def preview_next(self, graph_id=None, *, limit=1):
            return [
                ScheduleDecision(
                    decision_id="d1",
                    at="2026-07-09T00:00:00Z",
                    graph_id="g1",
                    node_id="n1",
                    score=1.0,
                    dispatch_hints={"project": "p", "repository": "p/r"},
                )
            ]

        def next(self, graph_id=None, *, limit=1):
            return []

    svc = AosService(str(tmp_path), scheduler=Sched())
    result = svc.next(apply_hints=True, agent_id=None)
    assert isinstance(result, Exception)


def test_apply_hints_calls_binder(tmp_path) -> None:
    calls: list[str] = []

    class Sched:
        def preview_next(self, graph_id=None, *, limit=1):
            return [
                ScheduleDecision(
                    decision_id="d1",
                    at="2026-07-09T00:00:00Z",
                    graph_id="g1",
                    node_id="n1",
                    score=1.0,
                    dispatch_hints={"project": "p", "repository": "p/r", "title": "t"},
                    acl_commands=["x"],
                )
            ]

        def next(self, graph_id=None, *, limit=1):
            return []

    def bind(session_root, *, agent_id, decision):
        _ = session_root, decision
        calls.append(agent_id)
        return ["lease-1", "wt-1"]

    svc = AosService(str(tmp_path), scheduler=Sched(), apply_acl_fn=bind)
    result = svc.next(apply_hints=True, agent_id="agent-1")
    assert not isinstance(result, Exception)
    assert result.hints_applied is True
    assert calls == ["agent-1"]

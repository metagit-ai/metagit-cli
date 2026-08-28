#!/usr/bin/env python
"""Unit tests for routing run ledger show/replay/export and concurrency."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from metagit.core.config.models import MetagitConfig, RoutingConfig
from metagit.core.routing.models import RequestClass
from metagit.core.routing.redaction import redact_run
from metagit.core.routing.routing_service import RoutingService


def _service(tmp_path: Path) -> RoutingService:
    catalog = tmp_path / "knowledge" / "requests" / "entries"
    runs = tmp_path / "knowledge" / "requests" / "runs"
    catalog.mkdir(parents=True)
    runs.mkdir(parents=True)
    config = MetagitConfig(
        name="ws",
        routing=RoutingConfig(
            catalog="knowledge/requests/entries",
            runs="knowledge/requests/runs",
        ),
    )
    service = RoutingService(config, workspace_root=str(tmp_path))
    service.class_store.save(
        RequestClass(
            id="REQ-X",
            title="Example",
            triggers=["example"],
            tier="skilled",
            mutates=False,
        ),
        expected=None,
    )
    return service


def test_show_replay_export_and_redaction(tmp_path: Path) -> None:
    service = _service(tmp_path)
    opened = service.open_run(class_id="REQ-X", actor="agent-a")
    service.append_step(
        run_id=opened.id,
        name="acl_bind",
        status="ok",
        detail={"token": "secret-value", "note": "api_key=abc123"},
        intent="bind lease",
    )
    shown = service.show_run(opened.id, redact=True)
    assert shown.evidence.redacted is True
    assert "secret" not in str(shown.evidence.steps[0].detail).lower() or "[REDACTED]" in str(
        shown.evidence.steps[0].detail
    )
    replay = service.replay(opened.id)
    assert replay["dry_run"] is True
    assert replay["run_id"] == opened.id
    assert len(replay["steps"]) >= 1
    exported = service.export_runs(class_id="REQ-X")
    assert len(exported) == 1
    assert exported[0]["id"] == opened.id


def test_concurrent_open_run_writers(tmp_path: Path) -> None:
    service = _service(tmp_path)
    now = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)

    def _open(actor: str):
        local = RoutingService(
            MetagitConfig(
                name="ws",
                routing=RoutingConfig(
                    catalog="knowledge/requests/entries",
                    runs="knowledge/requests/runs",
                ),
            ),
            workspace_root=str(tmp_path),
            now_fn=lambda: now,
        )
        return local.open_run(class_id="REQ-X", actor=actor)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_open, f"agent-{idx}") for idx in range(8)]
        runs = [fut.result() for fut in futures]
    ids = {row.id for row in runs}
    assert len(ids) == 8
    listed = service.list_runs(class_id="REQ-X")
    assert len(listed) == 8


def test_record_aos_next_ensures_system_class(tmp_path: Path) -> None:
    service = _service(tmp_path)
    run = service.record_aos_next(actor="agent-1", decision={"node_id": "n1"})
    assert run.cls == "REQ-AOS-NEXT"
    assert run.evidence.steps[0].name == "aos_next"
    cls, _ = service.class_store.load("REQ-AOS-NEXT")
    assert cls is not None


def test_redact_run_marks_evidence() -> None:
    from metagit.core.routing.models import Run, RunEvidence, ControlLoopStep

    run = Run(
        id="RUN-1",
        **{"class": "REQ-X"},
        tier="skilled",
        actor="a",
        opened="2026-08-27T00:00:00Z",
        evidence=RunEvidence(
            steps=[
                ControlLoopStep(
                    name="x",
                    at="2026-08-27T00:00:00Z",
                    detail={"Authorization": "Bearer abcdefghijklmnop"},
                )
            ]
        ),
    )
    redacted = redact_run(run)
    assert redacted.evidence.redacted is True
    assert "[REDACTED]" in str(redacted.evidence.steps[0].detail)

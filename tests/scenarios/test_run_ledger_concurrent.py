#!/usr/bin/env python
"""Optional — concurrent run-ledger writers (RFC-0017 pattern reuse)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from metagit.core.config.models import MetagitConfig, RoutingConfig
from metagit.core.routing.models import RequestClass
from metagit.core.routing.routing_service import RoutingService

from tests.scenarios.harness.workspace import ScenarioWorkspace


def test_run_ledger_concurrent_writers(tmp_path: Path) -> None:
    """Reuse the unit-test concurrent open_run pattern inside a scenario workspace."""
    ws = ScenarioWorkspace.bootstrap(tmp_path, ready_nodes=0)
    catalog = ws.root / "knowledge" / "requests" / "entries"
    runs = ws.root / "knowledge" / "requests" / "runs"
    catalog.mkdir(parents=True)
    runs.mkdir(parents=True)
    config = MetagitConfig(
        name="scenario-workspace",
        routing=RoutingConfig(
            catalog="knowledge/requests/entries",
            runs="knowledge/requests/runs",
        ),
    )
    seed = RoutingService(config, workspace_root=str(ws.root))
    seed.class_store.save(
        RequestClass(
            id="REQ-X",
            title="Example",
            triggers=["example"],
            tier="skilled",
            mutates=False,
        ),
        expected=None,
    )
    now = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)

    def _open(actor: str):
        local = RoutingService(
            MetagitConfig(
                name="scenario-workspace",
                routing=RoutingConfig(
                    catalog="knowledge/requests/entries",
                    runs="knowledge/requests/runs",
                ),
            ),
            workspace_root=str(ws.root),
            now_fn=lambda: now,
        )
        return local.open_run(class_id="REQ-X", actor=actor)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_open, f"agent-{idx}") for idx in range(8)]
        opened = [fut.result() for fut in futures]
    assert len({row.id for row in opened}) == 8
    listed = seed.list_runs(class_id="REQ-X")
    assert len(listed) == 8

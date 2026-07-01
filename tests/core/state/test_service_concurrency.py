#!/usr/bin/env python
"""Concurrency retry tests for state-backed services."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from metagit.core.context.models import Objective
from metagit.core.context.objective_service import ObjectiveService
from metagit.core.context.objective_store import ObjectiveStore
from metagit.core.state.errors import StateConflictError
from metagit.core.workspace.context_models import utc_now_iso


def _objective(obj_id: str, title: str) -> Objective:
    now = utc_now_iso()
    return Objective(
        id=obj_id,
        title=title,
        status="pending",
        created_at=now,
        updated_at=now,
    )


def test_objective_service_retries_after_conflict(tmp_path) -> None:
    root = str(tmp_path)
    stale_store = ObjectiveStore(workspace_root=root)
    stale_store.load_objectives()

    service_a = ObjectiveService(workspace_root=root)
    service_a._store = stale_store
    service_b = ObjectiveService(workspace_root=root)

    service_b.upsert(_objective("obj-b", "Second"))
    saved = service_a.upsert(_objective("obj-a", "First"))
    assert saved.id == "obj-a"
    rows = service_a.list().objectives
    assert {row.id for row in rows} == {"obj-a", "obj-b"}


def test_objective_service_surfaces_conflict_when_retry_exhausted(tmp_path) -> None:
    service = ObjectiveService(workspace_root=str(tmp_path))
    objective = _objective("obj-a", "Only")

    with patch(
        "metagit.core.context.objective_service.with_state_retry",
        side_effect=StateConflictError("forced"),
    ):
        with pytest.raises(StateConflictError):
            service.upsert(objective)

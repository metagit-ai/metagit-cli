#!/usr/bin/env python
"""Tests for LocalFileBackend paths and tokens."""

from __future__ import annotations

import json

import pytest

from metagit.core.context.models import Objective
from metagit.core.state.errors import StateConflictError
from metagit.core.state.local import LocalFileBackend, local_bundle
from metagit.core.workspace.context_models import utc_now_iso


def test_local_paths_match_legacy_layout(tmp_path) -> None:
    backend = LocalFileBackend(workspace_root=str(tmp_path))
    assert backend.objectives_path == tmp_path / ".metagit" / "sessions" / "objectives.json"
    assert backend.handoffs_path == tmp_path / ".metagit" / "sessions" / "handoffs.json"
    assert backend.approvals_path == tmp_path / ".metagit" / "approvals" / "pending.json"


def test_local_objectives_envelope_keys_unchanged(tmp_path) -> None:
    backend = local_bundle(str(tmp_path)).objectives()
    now = utc_now_iso()
    objective = Objective(
        id="obj-1",
        title="Test",
        status="pending",
        created_at=now,
        updated_at=now,
    )
    backend.save([objective], expected=None)
    raw = json.loads((tmp_path / ".metagit" / "sessions" / "objectives.json").read_text())
    assert list(raw.keys()) == ["objectives"]


def test_local_token_changes_after_write(tmp_path) -> None:
    backend = local_bundle(str(tmp_path)).objectives()
    now = utc_now_iso()
    objective = Objective(
        id="obj-1",
        title="Test",
        status="pending",
        created_at=now,
        updated_at=now,
    )
    first_token = backend.save([objective], expected=None)
    _, second_token = backend.load()
    assert first_token == second_token
    objective2 = objective.model_copy(update={"title": "Updated"})
    new_token = backend.save([objective2], expected=second_token)
    assert new_token != second_token


def test_local_stale_token_raises_conflict(tmp_path) -> None:
    backend = local_bundle(str(tmp_path)).objectives()
    now = utc_now_iso()
    objective = Objective(
        id="obj-1",
        title="Test",
        status="pending",
        created_at=now,
        updated_at=now,
    )
    backend.save([objective], expected=None)
    with pytest.raises(StateConflictError):
        backend.save([objective], expected="deadbeef")

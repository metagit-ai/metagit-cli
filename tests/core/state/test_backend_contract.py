#!/usr/bin/env python
"""Shared backend contract tests for local and remote state backends."""

from __future__ import annotations

import uuid

import pytest

from metagit.core.context.models import HandoffItem, Objective
from metagit.core.state.base import BackendBundle
from metagit.core.state.errors import StateConflictError
from metagit.core.state.local import local_bundle
from metagit.core.workspace.context_models import utc_now_iso

BACKEND_FACTORIES = {
    "local": local_bundle,
}


@pytest.fixture(params=list(BACKEND_FACTORIES.keys()))
def backend_bundle(request, tmp_path):
    factory = BACKEND_FACTORIES[request.param]
    return factory(str(tmp_path))


def _sample_objective() -> Objective:
    now = utc_now_iso()
    return Objective(
        id="obj-1",
        title="Ship remote state",
        status="in_progress",
        repos=["platform/api"],
        created_at=now,
        updated_at=now,
    )


def test_load_empty_returns_none_token(backend_bundle: BackendBundle) -> None:
    objectives, token = backend_bundle.objectives().load()
    assert objectives == []
    assert token is None


def test_objectives_save_round_trip(backend_bundle: BackendBundle) -> None:
    backend = backend_bundle.objectives()
    sample = _sample_objective()
    token = backend.save([sample], expected=None)
    loaded, loaded_token = backend.load()
    assert len(loaded) == 1
    assert loaded[0].id == "obj-1"
    assert loaded_token == token


def test_objectives_stale_token_raises_conflict(backend_bundle: BackendBundle) -> None:
    backend = backend_bundle.objectives()
    backend.save([_sample_objective()], expected=None)
    with pytest.raises(StateConflictError):
        backend.save([_sample_objective()], expected="stale-token")


def test_handoff_append_without_prior_token(backend_bundle: BackendBundle) -> None:
    backend = backend_bundle.handoffs()
    now = utc_now_iso()
    item = HandoffItem(
        id=uuid.uuid4().hex,
        title="Investigate flake",
        created_by="agent-a",
        created_at=now,
        updated_at=now,
    )
    backend.append(item)
    rows, _ = backend.load()
    assert len(rows) == 1
    assert rows[0].title == "Investigate flake"

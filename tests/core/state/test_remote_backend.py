#!/usr/bin/env python
"""Tests for remote HTTP state backend."""

from __future__ import annotations

import uuid

import pytest

from metagit.core.context.models import HandoffItem, Objective
from metagit.core.state.errors import StateConflictError
from metagit.core.state.remote import remote_bundle
from metagit.core.workspace.context_models import utc_now_iso


def test_remote_objectives_round_trip(remote_stub_server: str) -> None:
    bundle = remote_bundle(remote_stub_server)
    backend = bundle.objectives()
    now = utc_now_iso()
    sample = Objective(
        id="remote-1",
        title="Remote objective",
        status="pending",
        created_at=now,
        updated_at=now,
    )
    token = backend.save([sample], expected=None)
    loaded, loaded_token = backend.load()
    assert len(loaded) == 1
    assert loaded[0].id == "remote-1"
    assert loaded_token == token


def test_remote_stale_put_raises_conflict(remote_stub_server: str) -> None:
    bundle = remote_bundle(remote_stub_server)
    backend = bundle.objectives()
    now = utc_now_iso()
    sample = Objective(
        id="remote-1",
        title="Remote objective",
        status="pending",
        created_at=now,
        updated_at=now,
    )
    backend.save([sample], expected=None)
    with pytest.raises(StateConflictError):
        backend.save([sample], expected="deadbeef")


def test_remote_handoff_append(remote_stub_server: str) -> None:
    backend = remote_bundle(remote_stub_server).handoffs()
    now = utc_now_iso()
    item = HandoffItem(
        id=uuid.uuid4().hex,
        title="Remote handoff",
        created_by="agent",
        created_at=now,
        updated_at=now,
    )
    backend.append(item)
    rows, _ = backend.load()
    assert len(rows) == 1
    assert rows[0].title == "Remote handoff"

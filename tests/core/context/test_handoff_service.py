"""Tests for HandoffService: create / claim / complete / list."""

from __future__ import annotations

import pytest

from metagit.core.context.handoff_service import HandoffService


@pytest.fixture
def service(tmp_path):
    """Return a HandoffService backed by a fresh temp directory."""
    (tmp_path / ".metagit.yml").write_text("workspace:\n  path: .\n")
    return HandoffService(workspace_root=str(tmp_path))


def test_create_returns_item_with_audit_event(service):
    row = service.create(title="Do the thing", created_by="agentA")
    assert row.id
    assert row.title == "Do the thing"
    assert row.status == "open"
    assert row.created_by == "agentA"
    assert len(row.events) == 1
    assert row.events[0].action == "create"


def test_list_returns_all_handoffs(service):
    service.create(title="First", created_by="agent")
    service.create(title="Second", created_by="agent")
    result = service.list()
    assert len(result.handoffs) == 2


def test_list_filters_by_status(service):
    service.create(title="Open one", created_by="agent")
    row = service.create(title="To claim", created_by="agent")
    service.claim(row.id, claimed_by="agentB", note=None)

    open_only = service.list(status="open")
    claimed_only = service.list(status="claimed")

    assert len(open_only.handoffs) == 1
    assert open_only.handoffs[0].title == "Open one"
    assert len(claimed_only.handoffs) == 1
    assert claimed_only.handoffs[0].title == "To claim"


def test_claim_sets_status_and_claimed_by(service):
    row = service.create(title="Claimable", created_by="agent")
    claimed = service.claim(row.id, claimed_by="agentB", note="taking this")
    assert claimed.status == "claimed"
    assert claimed.claimed_by == "agentB"
    actions = [ev.action for ev in claimed.events]
    assert "claim" in actions


def test_complete_sets_status_completed(service):
    row = service.create(title="Work", created_by="agent")
    service.claim(row.id, claimed_by="agentC", note=None)
    done = service.complete(row.id, actor="agentC", note="done!")
    assert done.status == "completed"
    actions = [ev.action for ev in done.events]
    assert "complete" in actions


def test_unknown_id_raises_value_error(service):
    with pytest.raises(ValueError, match="handoff not found"):
        service.claim("nonexistent-id", claimed_by="someone", note=None)


def test_handoffs_persist_across_instances(tmp_path):
    (tmp_path / ".metagit.yml").write_text("workspace:\n  path: .\n")
    svc1 = HandoffService(workspace_root=str(tmp_path))
    row = svc1.create(title="Persistent", created_by="agent")

    svc2 = HandoffService(workspace_root=str(tmp_path))
    result = svc2.list()
    ids = [r.id for r in result.handoffs]
    assert row.id in ids

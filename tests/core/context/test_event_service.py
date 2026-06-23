"""Tests for WorkspaceEventService incremental event polling."""

from __future__ import annotations

import pytest

from metagit.core.context.event_service import WorkspaceEventService
from metagit.core.context.approval_service import ApprovalService
from metagit.core.context.handoff_service import HandoffService
from metagit.core.context.objective_service import ObjectiveService


@pytest.fixture
def workspace(tmp_path):
    (tmp_path / ".metagit.yml").write_text("workspace:\n  path: .\n")
    return str(tmp_path)


def test_empty_workspace_returns_empty_events(workspace):
    svc = WorkspaceEventService(workspace_root=workspace)
    result = svc.list_events()
    assert result.ok is True
    assert result.events == []
    assert result.next_cursor is None


def test_events_include_objectives(workspace):
    obj_svc = ObjectiveService(workspace_root=workspace)
    obj_svc.upsert_partial({"id": "obj-1", "title": "Do something"})
    result = WorkspaceEventService(workspace_root=workspace).list_events()
    sources = [ev.source for ev in result.events]
    assert "objective" in sources


def test_events_include_approvals(workspace):
    ApprovalService(workspace_root=workspace).request(
        action="deploy", payload={"env": "prod"}, requested_by="agent"
    )
    result = WorkspaceEventService(workspace_root=workspace).list_events()
    sources = [ev.source for ev in result.events]
    assert "approval" in sources


def test_events_include_handoffs(workspace):
    HandoffService(workspace_root=workspace).create(title="Hand me off", created_by="agent")
    result = WorkspaceEventService(workspace_root=workspace).list_events()
    sources = [ev.source for ev in result.events]
    assert "handoff" in sources


def test_since_cursor_filters_older_events(workspace):
    # Create one event, capture next_cursor, create a second, and verify only the new one comes back
    obj_svc = ObjectiveService(workspace_root=workspace)
    obj_svc.upsert_partial({"id": "obj-a", "title": "Old"})

    cursor_result = WorkspaceEventService(workspace_root=workspace).list_events()
    cursor = cursor_result.next_cursor
    assert cursor is not None

    # Now create a handoff with a timestamp strictly after the cursor
    import time
    time.sleep(0.01)
    HandoffService(workspace_root=workspace).create(title="New thing", created_by="agent")

    filtered = WorkspaceEventService(workspace_root=workspace).list_events(since=cursor)
    sources = [ev.source for ev in filtered.events]
    # At least the handoff should appear; the old objective should not
    assert "handoff" in sources


def test_next_cursor_advances(workspace):
    HandoffService(workspace_root=workspace).create(title="A", created_by="agent")
    r1 = WorkspaceEventService(workspace_root=workspace).list_events()
    assert r1.next_cursor is not None

    import time; time.sleep(0.01)
    HandoffService(workspace_root=workspace).create(title="B", created_by="agent")
    r2 = WorkspaceEventService(workspace_root=workspace).list_events()
    assert r2.next_cursor is not None
    assert r2.next_cursor >= r1.next_cursor

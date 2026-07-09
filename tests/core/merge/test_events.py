#!/usr/bin/env python
"""Tests for merge event emission into the workspace feed."""

from __future__ import annotations

from pathlib import Path

from metagit.core.context.event_service import WorkspaceEventService
from metagit.core.merge.events import MergeEventStore


def test_merge_events_are_visible_in_workspace_event_feed(tmp_path: Path) -> None:
  session = tmp_path / "session"
  session.mkdir()
  event = MergeEventStore(str(session)).append(
    "MergeEnqueued",
    {
      "merge_id": "merge-001",
      "repository": "project/repo",
      "source_branch": "agent/change",
      "target_branch": "integration/test",
      "status": "queued",
    },
  )
  assert not isinstance(event, Exception)

  feed = WorkspaceEventService(str(session)).list_events()

  events = [
    item
    for item in feed.events
    if item.source == "merge" and item.kind == "MergeEnqueued"
  ]
  assert events
  assert events[0].id == event.event_id
  assert events[0].data["merge_id"] == "merge-001"

#!/usr/bin/env python
"""Tests for semantic event emission and workspace event merge."""

from __future__ import annotations

from pathlib import Path

from metagit.core.context.event_service import WorkspaceEventService
from metagit.core.semantic.service import SemanticGraphService


def test_declare_emits_semantic_workspace_event(tmp_path: Path) -> None:
  session = tmp_path / "session"
  session.mkdir()
  service = SemanticGraphService(str(session))
  declared = service.declare(
    concept="Authentication",
    repository="demo/api",
    patterns=["backend/auth/**"],
  )
  assert not isinstance(declared, Exception)

  feed = WorkspaceEventService(str(session)).list_events()

  events = [
    event
    for event in feed.events
    if event.source == "semantic" and event.kind == "ConceptDeclared"
  ]
  assert events
  assert events[0].data["concept_id"] == "authentication"

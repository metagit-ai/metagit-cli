#!/usr/bin/env python
"""Tests for semantic seed catalog and deterministic ingest hints."""

from __future__ import annotations

import json
from pathlib import Path

from metagit.core.context.event_service import WorkspaceEventService
from metagit.core.semantic.paths import graph_root
from metagit.core.semantic.service import SemanticGraphService


def test_seed_adds_static_catalog_idempotently(tmp_path: Path) -> None:
  session = tmp_path / "session"
  session.mkdir()
  service = SemanticGraphService(str(session))

  first = service.seed(repository="demo/api")
  second = service.seed(repository="demo/api")

  assert not isinstance(first, Exception)
  assert not isinstance(second, Exception)
  assert first.ok is True
  assert first.concepts_added > 0
  assert first.ownerships_added == first.concepts_added
  assert second.concepts_added == 0
  assert second.ownerships_added == 0

  auth = service.query(concept="Authentication")
  assert not isinstance(auth, Exception)
  assert auth.concept is not None
  assert [row.repository for row in auth.ownerships] == ["demo/api"]
  assert auth.ownerships[0].source == "seed"


def test_ingest_reads_hints_file_and_emits_event(tmp_path: Path) -> None:
  session = tmp_path / "session"
  session.mkdir()
  hints_path = graph_root(str(session)) / "ingest-hints.json"
  hints_path.parent.mkdir(parents=True, exist_ok=True)
  hints_path.write_text(
    json.dumps(
      {
        "ownerships": [
          {
            "concept": "Authentication",
            "repository": "demo/api",
            "patterns": ["**/auth/**"],
          }
        ]
      }
    ),
    encoding="utf-8",
  )
  service = SemanticGraphService(str(session))

  result = service.ingest()

  assert not isinstance(result, Exception)
  assert result.ok is True
  assert result.added == 1
  assert result.skipped == 0
  query = service.query(concept="authentication")
  assert not isinstance(query, Exception)
  assert query.concept is not None
  assert query.ownerships[0].source == "ingest"

  feed = WorkspaceEventService(str(session)).list_events()
  events = [
    event
    for event in feed.events
    if event.source == "semantic" and event.kind == "ConceptIngested"
  ]
  assert events
  assert events[0].data["added"] == 1


def test_ingest_noops_without_hints_file(tmp_path: Path) -> None:
  session = tmp_path / "session"
  session.mkdir()
  service = SemanticGraphService(str(session))

  result = service.ingest()

  assert not isinstance(result, Exception)
  assert result.ok is True
  assert result.added == 0
  assert result.skipped == 0
  assert result.reason == "no_ingest_signals"

#!/usr/bin/env python
"""Unit tests for SemanticGraphService declare/query/owners."""

from __future__ import annotations

from pathlib import Path

from metagit.core.semantic.service import SemanticGraphService


def test_declare_and_owners_round_trip(tmp_path: Path) -> None:
  session = tmp_path / "session"
  session.mkdir()
  svc = SemanticGraphService(str(session))
  declared = svc.declare(
    concept="Authentication",
    repository="demo/api",
    patterns=["**/auth/**"],
  )
  assert not isinstance(declared, Exception)
  assert declared.concept.concept_id == "authentication"

  owners = svc.owners(path="backend/auth/token.py", repository="demo/api")
  assert not isinstance(owners, Exception)
  assert any(c.concept_id == "authentication" for c in owners.concepts)

  query = svc.query(concept="authentication")
  assert not isinstance(query, Exception)
  assert query.concept is not None
  assert len(query.ownerships) == 1


def test_owners_miss_when_path_outside_pattern(tmp_path: Path) -> None:
  session = tmp_path / "session"
  session.mkdir()
  svc = SemanticGraphService(str(session))
  svc.declare(concept="Billing", repository="demo/api", patterns=["**/billing/**"])
  owners = svc.owners(path="backend/auth/token.py", repository="demo/api")
  assert not isinstance(owners, Exception)
  assert owners.concepts == []


def test_declare_returns_exception_for_bad_repository(tmp_path: Path) -> None:
  session = tmp_path / "session"
  session.mkdir()
  svc = SemanticGraphService(str(session))

  result = svc.declare(
    concept="Authentication",
    repository="api",
    patterns=["**/auth/**"],
  )

  assert isinstance(result, Exception)


def test_declare_returns_exception_for_empty_patterns(tmp_path: Path) -> None:
  session = tmp_path / "session"
  session.mkdir()
  svc = SemanticGraphService(str(session))

  result = svc.declare(
    concept="Authentication",
    repository="demo/api",
    patterns=[],
  )

  assert isinstance(result, Exception)


def test_query_matches_display_name_case_insensitive(tmp_path: Path) -> None:
  session = tmp_path / "session"
  session.mkdir()
  svc = SemanticGraphService(str(session))
  declared = svc.declare(
    concept="Authentication",
    repository="demo/api",
    patterns=["**/auth/**"],
  )
  assert not isinstance(declared, Exception)

  query = svc.query(concept="authentication")

  assert not isinstance(query, Exception)
  assert query.concept is not None
  assert query.concept.concept_id == "authentication"

#!/usr/bin/env python
"""Unit tests for SemanticGraphStore."""

from __future__ import annotations

from pathlib import Path

from metagit.core.semantic.models import Concept, ConceptOwnership
from metagit.core.semantic.paths import concepts_file, graph_root, ownerships_file
from metagit.core.semantic.store import SemanticGraphStore


def test_store_round_trips_concepts_and_ownerships(tmp_path: Path) -> None:
  session = tmp_path / "session"
  session.mkdir()
  store = SemanticGraphStore(str(session))
  concept = Concept(
    concept_id="auth",
    name="Authentication",
    aliases=["login"],
    created_at="2026-07-09T00:00:00+00:00",
    updated_at="2026-07-09T00:00:00+00:00",
  )
  ownership = ConceptOwnership(
    ownership_id="auth-owner",
    concept_id="auth",
    repository="core/api",
    patterns=["**/auth/**"],
    symbol_hints=["AuthService"],
    source="manual",
    created_at="2026-07-09T00:00:00+00:00",
    updated_at="2026-07-09T00:00:00+00:00",
  )

  concepts_err = store.save_concepts([concept])
  ownerships_err = store.save_ownerships([ownership])

  assert concepts_err is None
  assert ownerships_err is None
  assert graph_root(str(session)).is_dir()
  assert concepts_file(str(session)).is_file()
  assert ownerships_file(str(session)).is_file()

  loaded_concepts = store.load_concepts()
  loaded_ownerships = store.load_ownerships()

  assert not isinstance(loaded_concepts, Exception)
  assert not isinstance(loaded_ownerships, Exception)
  assert loaded_concepts[0].concept_id == "auth"
  assert loaded_concepts[0].aliases == ["login"]
  assert loaded_ownerships[0].repository == "core/api"
  assert loaded_ownerships[0].symbol_hints == ["AuthService"]


def test_store_empty_load_returns_empty_lists(tmp_path: Path) -> None:
  session = tmp_path / "session"
  session.mkdir()
  store = SemanticGraphStore(str(session))

  concepts = store.load_concepts()
  ownerships = store.load_ownerships()

  assert concepts == []
  assert ownerships == []


def test_store_update_concepts_and_ownerships(tmp_path: Path) -> None:
  session = tmp_path / "session"
  session.mkdir()
  store = SemanticGraphStore(str(session))
  concept = Concept(
    concept_id="auth",
    name="Authentication",
    aliases=[],
    created_at="2026-07-09T00:00:00+00:00",
    updated_at="2026-07-09T00:00:00+00:00",
  )
  ownership = ConceptOwnership(
    ownership_id="auth-owner",
    concept_id="auth",
    repository="core/api",
    patterns=["**/auth/**"],
    created_at="2026-07-09T00:00:00+00:00",
    updated_at="2026-07-09T00:00:00+00:00",
  )

  concepts = store.update_concepts(lambda rows: [*rows, concept])
  ownerships = store.update_ownerships(lambda rows: [*rows, ownership])

  assert not isinstance(concepts, Exception)
  assert not isinstance(ownerships, Exception)
  assert concepts == [concept]
  assert ownerships == [ownership]
  assert store.load_concepts() == [concept]
  assert store.load_ownerships() == [ownership]

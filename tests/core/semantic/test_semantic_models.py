#!/usr/bin/env python
"""Unit tests for semantic graph models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from metagit.core.semantic.models import Concept, ConceptOwnership


def test_concept_rejects_invalid_concept_id() -> None:
  with pytest.raises(ValidationError):
    Concept(
      concept_id="Bad Id!",
      name="Bad concept",
      created_at="2026-07-09T00:00:00+00:00",
      updated_at="2026-07-09T00:00:00+00:00",
    )


def test_concept_rejects_empty_name() -> None:
  with pytest.raises(ValidationError):
    Concept(
      concept_id="auth",
      name="  ",
      created_at="2026-07-09T00:00:00+00:00",
      updated_at="2026-07-09T00:00:00+00:00",
    )


def test_ownership_requires_at_least_one_pattern() -> None:
  with pytest.raises(ValidationError):
    ConceptOwnership(
      ownership_id="auth-owner",
      concept_id="auth",
      repository="core/api",
      patterns=[],
      created_at="2026-07-09T00:00:00+00:00",
      updated_at="2026-07-09T00:00:00+00:00",
    )


def test_ownership_rejects_invalid_repository() -> None:
  for repository in ["api", "a/b/c"]:
    with pytest.raises(ValidationError):
      ConceptOwnership(
        ownership_id="auth-owner",
        concept_id="auth",
        repository=repository,
        patterns=["**/auth/**"],
        created_at="2026-07-09T00:00:00+00:00",
        updated_at="2026-07-09T00:00:00+00:00",
      )


def test_ownership_rejects_whitespace_only_patterns() -> None:
  with pytest.raises(ValidationError):
    ConceptOwnership(
      ownership_id="auth-owner",
      concept_id="auth",
      repository="core/api",
      patterns=["  ", "\t"],
      created_at="2026-07-09T00:00:00+00:00",
      updated_at="2026-07-09T00:00:00+00:00",
    )


def test_valid_ownership_accepts_glob_pattern() -> None:
  ownership = ConceptOwnership(
    ownership_id="auth-owner",
    concept_id="auth",
    repository="core/api",
    patterns=["**/auth/**"],
    created_at="2026-07-09T00:00:00+00:00",
    updated_at="2026-07-09T00:00:00+00:00",
  )

  assert ownership.repository == "core/api"
  assert ownership.patterns == ["**/auth/**"]
  assert ownership.source == "manual"

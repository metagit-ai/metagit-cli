#!/usr/bin/env python
"""Unit tests for Atlas validation."""

from __future__ import annotations

from metagit.core.atlas.models import EntityEnvelope
from metagit.core.atlas.validate import ValidationIssue, validate_entities


def test_dangling_invariant_ref_is_error() -> None:
  cap = EntityEnvelope.model_validate(
    {
      "apiVersion": "atlas.metagit.dev/v1alpha1",
      "kind": "Capability",
      "metadata": {
        "id": "capability:refund.issue",
        "name": "Issue Refund",
        "lifecycle": "active",
        "classification": "internal",
        "provenance": {"source": "curated", "updatedAt": "2026-07-14T00:00:00Z"},
      },
      "spec": {"invariants": ["invariant:missing"]},
    }
  )
  issues = validate_entities([cap])
  assert any(i.code == "dangling_ref" for i in issues)


def test_valid_pair_passes() -> None:
  inv = EntityEnvelope.model_validate(
    {
      "apiVersion": "atlas.metagit.dev/v1alpha1",
      "kind": "Invariant",
      "metadata": {
        "id": "invariant:refund.idempotent",
        "name": "Refund idempotent",
        "lifecycle": "active",
        "classification": "internal",
        "provenance": {"source": "curated", "updatedAt": "2026-07-14T00:00:00Z"},
      },
      "spec": {"statement": "Same key => one effect"},
    }
  )
  cap = EntityEnvelope.model_validate(
    {
      "apiVersion": "atlas.metagit.dev/v1alpha1",
      "kind": "Capability",
      "metadata": {
        "id": "capability:refund.issue",
        "name": "Issue Refund",
        "lifecycle": "active",
        "classification": "internal",
        "provenance": {"source": "curated", "updatedAt": "2026-07-14T00:00:00Z"},
      },
      "spec": {"invariants": ["invariant:refund.idempotent"]},
    }
  )
  issues = validate_entities([cap, inv])
  assert issues == []

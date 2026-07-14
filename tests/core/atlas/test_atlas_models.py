#!/usr/bin/env python
"""Unit tests for Atlas models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from metagit.core.atlas.models import AtlasConfig, EntityEnvelope, EvidenceItem


def test_entity_envelope_requires_id_and_kind() -> None:
  row = EntityEnvelope.model_validate(
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
      "spec": {"purpose": "Refund funds"},
    }
  )
  assert row.metadata.id == "capability:refund.issue"
  with pytest.raises(ValidationError):
    EntityEnvelope.model_validate(
      {
        "apiVersion": "atlas.metagit.dev/v1alpha1",
        "kind": "Capability",
        "metadata": {
          "id": "bad id",
          "name": "X",
          "lifecycle": "active",
          "classification": "internal",
          "provenance": {"source": "curated", "updatedAt": "2026-07-14T00:00:00Z"},
        },
        "spec": {},
      }
    )


def test_evidence_confidence_bounds() -> None:
  ok = EvidenceItem(
    id="evidence:symbol:a",
    kind="symbol",
    locator="src/a.py#f",
    revision="abc",
    extractor="python-ast@1.0.0",
    observedAt="2026-07-14T00:00:00Z",
    confidence=1.0,
  )
  assert ok.confidence == 1.0
  with pytest.raises(ValidationError):
    EvidenceItem(
      id="evidence:symbol:a",
      kind="symbol",
      locator="src/a.py#f",
      revision="abc",
      extractor="python-ast@1.0.0",
      observedAt="2026-07-14T00:00:00Z",
      confidence=1.5,
    )


def test_atlas_config_defaults() -> None:
  cfg = AtlasConfig(repository="github.com/acme/toy", formatVersion="v1alpha1")
  assert cfg.commitGenerated is True
  assert cfg.apiVersion == "atlas.metagit.dev/v1alpha1"

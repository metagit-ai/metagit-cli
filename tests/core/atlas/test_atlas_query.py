#!/usr/bin/env python
"""Unit tests for Atlas local query (get / list / traverse / DSL)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from metagit.core.atlas.paths import capabilities_file, semantic_to_evidence_file
from metagit.core.atlas.query import AtlasQuery
from metagit.core.atlas.serialize import dump_yaml
from metagit.core.atlas.service import AtlasService
from metagit.core.atlas.store import AtlasStore

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "atlas" / "python_toy"

_REFUND_CAPABILITY = {
  "apiVersion": "atlas.metagit.dev/v1alpha1",
  "kind": "Capability",
  "metadata": {
    "id": "capability:refund.issue",
    "name": "Issue refund",
    "lifecycle": "active",
    "classification": "internal",
    "provenance": {"source": "curated"},
  },
  "spec": {"purpose": "Issue a refund for an order"},
}

_REFUND_MAPPING = {
  "mappings": [
    {
      "semantic": "capability:refund.issue",
      "relation": "maps_to",
      "evidence": [
        "evidence:symbol:src/toy/refunds.py#RefundService.issue",
      ],
    },
    {
      "semantic": "capability:refund.issue",
      "relation": "verified_by",
      "evidence": [
        "evidence:test:tests/test_refunds.py#test_issue_idempotent",
      ],
    },
  ],
}


@pytest.fixture
def toy_with_atlas(tmp_path: Path) -> Path:
  """Copy python_toy, init+generate Atlas, seed capability + mapping, rebuild index."""
  repo_root = tmp_path / "python_toy"
  shutil.copytree(FIXTURE, repo_root)
  service = AtlasService(repo_root)
  assert service.init(repository="local/python-toy").ok
  assert service.generate().ok

  capabilities_file(repo_root).write_text(
    dump_yaml({"entities": [_REFUND_CAPABILITY]}),
    encoding="utf-8",
  )
  semantic_to_evidence_file(repo_root).write_text(
    dump_yaml(_REFUND_MAPPING),
    encoding="utf-8",
  )
  rebuilt = AtlasStore(repo_root).rebuild_index()
  assert rebuilt is None
  return repo_root


def test_traverse_capability_to_evidence(toy_with_atlas: Path) -> None:
  q = AtlasQuery(toy_with_atlas)
  result = q.traverse(
    "capability:refund.issue",
    relations=["maps_to", "implements", "verified_by"],
  )
  assert not isinstance(result, Exception)
  assert result.ok
  assert len(result.nodes) >= 1
  node_ids = {node.get("id") for node in result.nodes}
  assert "evidence:symbol:src/toy/refunds.py#RefundService.issue" in node_ids


def test_list_entities_by_kind(toy_with_atlas: Path) -> None:
  q = AtlasQuery(toy_with_atlas)
  result = q.list_entities(kind="Capability")
  assert not isinstance(result, Exception)
  assert result.ok
  ids = {
    entity.get("metadata", {}).get("id") if isinstance(entity.get("metadata"), dict) else entity.get("id")
    for entity in result.entities
  }
  assert "capability:refund.issue" in ids


def test_dsl_query_by_id(toy_with_atlas: Path) -> None:
  q = AtlasQuery(toy_with_atlas)
  result = q.query('Capability[id="capability:refund.issue"]')
  assert not isinstance(result, Exception)
  assert result.ok
  assert result.entity is not None
  metadata = result.entity.get("metadata") if isinstance(result.entity, dict) else None
  entity_id = metadata.get("id") if isinstance(metadata, dict) else result.entity.get("id")
  assert entity_id == "capability:refund.issue"

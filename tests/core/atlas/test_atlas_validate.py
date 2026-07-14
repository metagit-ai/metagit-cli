#!/usr/bin/env python
"""Unit tests for Atlas validation."""

from __future__ import annotations

from pathlib import Path

from metagit.core.atlas.models import EntityEnvelope
from metagit.core.atlas.validate import (
  _schemas_dir,
  validate_config_dict,
  validate_entities,
)


def test_schemas_dir_resolves_packaged_data() -> None:
  schemas_dir = _schemas_dir()
  assert schemas_dir.is_dir()
  assert (schemas_dir / "atlas-config.schema.json").is_file()
  assert (schemas_dir / "entity.schema.json").is_file()
  assert schemas_dir.parts[-3:] == ("data", "schemas", "atlas")


def test_repo_and_packaged_atlas_schemas_stay_in_sync() -> None:
  packaged = Path(__file__).resolve().parents[3] / "src" / "metagit" / "data" / "schemas" / "atlas"
  repo = Path(__file__).resolve().parents[3] / "schemas" / "atlas"
  packaged_names = sorted(path.name for path in packaged.glob("*.json"))
  repo_names = sorted(path.name for path in repo.glob("*.json"))
  assert packaged_names == repo_names
  for name in packaged_names:
    assert (packaged / name).read_bytes() == (repo / name).read_bytes()


def test_validate_config_dict_loads_packaged_schema() -> None:
  issues = validate_config_dict(
    {
      "repository": "example/repo",
      "formatVersion": "1",
    }
  )
  assert issues == []


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

#!/usr/bin/env python
"""Unit tests for Atlas store and index."""

from __future__ import annotations

from pathlib import Path

from metagit.core.atlas.models import AtlasConfig
from metagit.core.atlas.paths import atlas_yaml_path, domain_file, index_entities_file, inventory_file
from metagit.core.atlas.store import AtlasStore


def test_init_layout_and_atomic_generated(tmp_path: Path) -> None:
  store = AtlasStore(tmp_path)
  cfg = AtlasConfig(repository="local/python-toy", formatVersion="v1alpha1")
  assert store.init_layout(cfg) is None
  assert atlas_yaml_path(tmp_path).is_file()
  assert store.write_generated({"inventory.yaml": {"files": [], "provenance": {"extractor": "inventory@1.0.0"}}}) is None
  assert inventory_file(tmp_path).is_file()
  # curated path must still exist and not be wiped
  assert (tmp_path / ".atlas" / "ontology").is_dir()


def test_index_rebuild_writes_json(tmp_path: Path) -> None:
  store = AtlasStore(tmp_path)
  store.init_layout(AtlasConfig(repository="local/x", formatVersion="v1alpha1"))
  store.write_generated({"inventory.yaml": {"files": [{"path": "a.py"}], "provenance": {"extractor": "inventory@1.0.0"}}})
  assert store.rebuild_index() is None
  assert index_entities_file(tmp_path).is_file()


def test_write_generated_preserves_curated_ontology(tmp_path: Path) -> None:
  store = AtlasStore(tmp_path)
  store.init_layout(AtlasConfig(repository="local/x", formatVersion="v1alpha1"))
  domain_path = domain_file(tmp_path)
  original = "entities:\n  - id: domain:payments\n    name: Payments\n"
  domain_path.write_text(original, encoding="utf-8")

  result = store.write_generated(
    {"inventory.yaml": {"files": [], "provenance": {"extractor": "inventory@1.0.0"}}},
  )

  assert result is None
  assert domain_path.read_text(encoding="utf-8") == original


def test_write_generated_rejects_path_traversal(tmp_path: Path) -> None:
  store = AtlasStore(tmp_path)
  store.init_layout(AtlasConfig(repository="local/x", formatVersion="v1alpha1"))
  domain_path = domain_file(tmp_path)
  original = "entities:\n  - id: domain:payments\n    name: Payments\n"
  domain_path.write_text(original, encoding="utf-8")

  result = store.write_generated(
    {"../ontology/domain.yaml": {"entities": [{"id": "evil", "name": "Evil"}]}},
  )

  assert isinstance(result, Exception)
  assert domain_path.read_text(encoding="utf-8") == original


def test_init_layout_preserves_existing_atlas_yaml(tmp_path: Path) -> None:
  store = AtlasStore(tmp_path)
  cfg = AtlasConfig(repository="local/x", formatVersion="v1alpha1")
  assert store.init_layout(cfg) is None
  atlas_path = atlas_yaml_path(tmp_path)
  original = atlas_path.read_text(encoding="utf-8")
  custom = "repository: local/custom\nformatVersion: v1alpha1\n"
  atlas_path.write_text(custom, encoding="utf-8")

  assert store.init_layout(cfg) is None
  assert atlas_path.read_text(encoding="utf-8") == custom
  assert atlas_path.read_text(encoding="utf-8") != original

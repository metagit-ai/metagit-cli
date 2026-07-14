#!/usr/bin/env python
"""Unit tests for Atlas store and index."""

from __future__ import annotations

from pathlib import Path

from metagit.core.atlas.models import AtlasConfig
from metagit.core.atlas.paths import atlas_yaml_path, index_entities_file, inventory_file
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

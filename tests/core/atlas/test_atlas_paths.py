#!/usr/bin/env python
"""Unit tests for Atlas path helpers."""

from __future__ import annotations

from pathlib import Path

from metagit.core.atlas.paths import (
  ATLAS_DIRNAME,
  atlas_root,
  capabilities_file,
  generated_dir,
  index_dir,
  inventory_file,
)


def test_layout_under_repo_root(tmp_path: Path) -> None:
  root = atlas_root(tmp_path)
  assert root == tmp_path / ATLAS_DIRNAME
  assert capabilities_file(tmp_path) == root / "ontology" / "capabilities.yaml"
  assert inventory_file(tmp_path) == root / "generated" / "inventory.yaml"
  assert index_dir(tmp_path) == root / "index"
  assert generated_dir(tmp_path).name == "generated"

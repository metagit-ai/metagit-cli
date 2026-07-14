#!/usr/bin/env python
"""Read/write Atlas curated and generated artifacts under ``.atlas/``."""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from metagit.core.atlas.index import rebuild_entities_index
from metagit.core.atlas.models import AtlasConfig, EntityEnvelope
from metagit.core.atlas.paths import (
  access_file,
  atlas_root,
  atlas_yaml_path,
  capabilities_file,
  classifications_file,
  concepts_file,
  contracts_dir,
  decisions_dir,
  domain_file,
  extensions_dir,
  external_ids_file,
  federation_dir,
  federation_export_file,
  federation_imports_dir,
  generated_dir,
  generated_imports_dir,
  generation_file,
  index_dir,
  intent_dir,
  invariants_dir,
  links_file,
  manifests_dir,
  mappings_dir,
  ontology_dir,
  ownership_dir,
  overrides_dir,
  policy_dir,
  risks_dir,
  semantic_to_evidence_file,
  suppressions_file,
)
from metagit.core.atlas.serialize import dump_yaml, load_yaml

_README_TEXT = """# Metagit Atlas

This directory holds the repository Atlas (RFC-0014).

- `ontology/` and `intent/` — curated semantic metadata (do not overwrite via generate)
- `generated/` — extractor output; replaced atomically by `metagit atlas generate`
- `mappings/` and `overrides/` — curated links and corrections
- `policy/` — access and generation policy
- `index/` — derived cache (gitignored); rebuild with generate/refresh
"""

_ENTITIES_STUB: dict[str, list[Any]] = {"entities": []}
_EMPTY_STUB: dict[str, Any] = {}


class AtlasStore:
  """Filesystem store for curated Atlas YAML and generated evidence."""

  def __init__(self, repo_root: str | Path) -> None:
    self._repo_root = Path(repo_root)

  @property
  def repo_root(self) -> Path:
    return self._repo_root

  def init_layout(self, cfg: AtlasConfig) -> None | Exception:
    """Create ``.atlas/`` directories, stubs, README, and ``atlas.yaml``."""
    try:
      root = atlas_root(self._repo_root)
      root.mkdir(parents=True, exist_ok=True)

      for directory in (
        ontology_dir(self._repo_root),
        extensions_dir(self._repo_root),
        intent_dir(self._repo_root),
        contracts_dir(self._repo_root),
        invariants_dir(self._repo_root),
        decisions_dir(self._repo_root),
        risks_dir(self._repo_root),
        ownership_dir(self._repo_root),
        generated_dir(self._repo_root),
        generated_imports_dir(self._repo_root),
        manifests_dir(self._repo_root),
        mappings_dir(self._repo_root),
        overrides_dir(self._repo_root),
        federation_dir(self._repo_root),
        federation_imports_dir(self._repo_root),
        policy_dir(self._repo_root),
        index_dir(self._repo_root),
      ):
        directory.mkdir(parents=True, exist_ok=True)

      stubs: list[tuple[Path, dict[str, Any]]] = [
        (domain_file(self._repo_root), _ENTITIES_STUB),
        (concepts_file(self._repo_root), _ENTITIES_STUB),
        (capabilities_file(self._repo_root), _ENTITIES_STUB),
        (semantic_to_evidence_file(self._repo_root), _EMPTY_STUB),
        (external_ids_file(self._repo_root), _EMPTY_STUB),
        (classifications_file(self._repo_root), _EMPTY_STUB),
        (links_file(self._repo_root), _EMPTY_STUB),
        (suppressions_file(self._repo_root), _EMPTY_STUB),
        (access_file(self._repo_root), _EMPTY_STUB),
        (generation_file(self._repo_root), _EMPTY_STUB),
        (federation_export_file(self._repo_root), _EMPTY_STUB),
      ]
      for path, payload in stubs:
        if not path.is_file():
          path.write_text(dump_yaml(payload), encoding="utf-8")

      readme = root / "README.md"
      if not readme.is_file():
        readme.write_text(_README_TEXT, encoding="utf-8")

      atlas_yaml_path(self._repo_root).write_text(
        dump_yaml(cfg.model_dump(mode="json", exclude_none=True)),
        encoding="utf-8",
      )
      return None
    except Exception as exc:  # noqa: BLE001
      return exc

  def write_generated(self, files: dict[str, Any]) -> None | Exception:
    """Atomically replace ``generated/`` with validated YAML payloads.

    Curated directories (ontology, intent, mappings, overrides) are never touched.
    """
    try:
      root = atlas_root(self._repo_root)
      root.mkdir(parents=True, exist_ok=True)
      token = uuid.uuid4().hex
      temp_dir = root / f".tmp-generated-{token}"
      old_dir = root / f".tmp-generated-old-{token}"
      target = generated_dir(self._repo_root)

      if temp_dir.exists():
        shutil.rmtree(temp_dir)
      temp_dir.mkdir(parents=True, exist_ok=False)

      try:
        for relative, payload in files.items():
          text = dump_yaml(payload)
          roundtrip = load_yaml(text)
          if roundtrip is None and payload is not None:
            raise ValueError(f"YAML round-trip failed for {relative}")
          dest = temp_dir / relative
          dest.parent.mkdir(parents=True, exist_ok=True)
          dest.write_text(text, encoding="utf-8")

        if target.exists():
          os.rename(target, old_dir)
        os.rename(temp_dir, target)
        if old_dir.exists():
          shutil.rmtree(old_dir)
      except Exception:
        if temp_dir.exists():
          shutil.rmtree(temp_dir, ignore_errors=True)
        if old_dir.exists() and not target.exists():
          os.rename(old_dir, target)
        raise

      return None
    except Exception as exc:  # noqa: BLE001
      return exc

  def load_curated_entities(self) -> list[EntityEnvelope] | Exception:
    """Load ``entities:`` lists from ontology and intent YAML files."""
    try:
      entities: list[EntityEnvelope] = []
      for directory in (
        ontology_dir(self._repo_root),
        intent_dir(self._repo_root),
      ):
        if not directory.is_dir():
          continue
        for path in sorted(directory.rglob("*.yaml")):
          loaded = load_yaml(path.read_text(encoding="utf-8"))
          if not isinstance(loaded, dict):
            continue
          raw_entities = loaded.get("entities")
          if not isinstance(raw_entities, list):
            continue
          for item in raw_entities:
            if not isinstance(item, dict):
              continue
            entities.append(EntityEnvelope.model_validate(item))
      return entities
    except Exception as exc:  # noqa: BLE001
      return exc

  def rebuild_index(self) -> None | Exception:
    """Rebuild ``.atlas/index/entities.json`` from curated + generated data."""
    return rebuild_entities_index(self._repo_root)


__all__ = [
  "AtlasStore",
]

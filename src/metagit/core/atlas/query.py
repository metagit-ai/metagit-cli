#!/usr/bin/env python
"""Local Atlas query: get, list, traverse, and a minimal DSL."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from metagit.core.atlas.models import AtlasQueryResult, EntityEnvelope
from metagit.core.atlas.paths import (
  index_entities_file,
  semantic_to_evidence_file,
  symbols_file,
  verifications_file,
)
from metagit.core.atlas.serialize import load_yaml
from metagit.core.atlas.store import AtlasStore

_DEFAULT_TRAVERSE_RELATIONS = ("maps_to", "implements", "verified_by")
_DSL_RE = re.compile(
  r"^(?P<kind>[A-Za-z][A-Za-z0-9_]*)\[id=(?P<quote>[\"'])(?P<id>[^\"']+)(?P=quote)\]\s*$"
)


class AtlasQuery:
  """Read-only local query over curated entities, mappings, and generated evidence."""

  def __init__(self, repo_root: str | Path) -> None:
    self._repo_root = Path(repo_root)
    self._store = AtlasStore(self._repo_root)

  def get_entity(self, entity_id: str) -> AtlasQueryResult | Exception:
    """Return a single curated entity by id."""
    try:
      entities = self._load_curated()
      if isinstance(entities, Exception):
        return entities
      for entity in entities:
        if entity.metadata.id == entity_id:
          payload = entity.model_dump(mode="json")
          return AtlasQueryResult(ok=True, entity=payload, entities=[payload])
      return AtlasQueryResult(ok=False)
    except Exception as exc:  # noqa: BLE001
      return exc

  def list_entities(self, *, kind: str | None = None) -> AtlasQueryResult | Exception:
    """List curated entities, optionally filtered by kind."""
    try:
      entities = self._load_curated()
      if isinstance(entities, Exception):
        return entities
      filtered = [
        entity.model_dump(mode="json")
        for entity in entities
        if kind is None or entity.kind == kind
      ]
      return AtlasQueryResult(ok=True, entities=filtered)
    except Exception as exc:  # noqa: BLE001
      return exc

  def traverse(
    self,
    start_id: str,
    *,
    relations: list[str] | None = None,
  ) -> AtlasQueryResult | Exception:
    """One-hop traverse from a semantic id through curated mappings to evidence."""
    try:
      allowed = set(relations or _DEFAULT_TRAVERSE_RELATIONS)
      mappings = self._load_mappings()
      if isinstance(mappings, Exception):
        return mappings
      evidence_index = self._load_evidence_index()
      if isinstance(evidence_index, Exception):
        return evidence_index

      nodes: list[dict[str, Any]] = []
      seen: set[str] = set()

      start = self.get_entity(start_id)
      if isinstance(start, Exception):
        return start
      if start.ok and start.entity is not None:
        start_node = {
          **start.entity,
          "id": start_id,
          "relation": None,
        }
        nodes.append(start_node)
        seen.add(start_id)

      for mapping in mappings:
        semantic = mapping.get("semantic")
        relation = mapping.get("relation")
        if semantic != start_id or not isinstance(relation, str) or relation not in allowed:
          continue
        evidence_ids = mapping.get("evidence")
        if not isinstance(evidence_ids, list):
          continue
        for evidence_id in evidence_ids:
          if not isinstance(evidence_id, str) or evidence_id in seen:
            continue
          node = evidence_index.get(evidence_id, {"id": evidence_id, "kind": "evidence"})
          nodes.append({**node, "id": evidence_id, "relation": relation})
          seen.add(evidence_id)

      return AtlasQueryResult(ok=True, nodes=nodes)
    except Exception as exc:  # noqa: BLE001
      return exc

  def query(self, expression: str) -> AtlasQueryResult | Exception:
    """Evaluate a minimal DSL expression or bare entity id."""
    try:
      stripped = expression.strip()
      if not stripped:
        return ValueError("query expression is required")

      match = _DSL_RE.match(stripped)
      if match is not None:
        kind = match.group("kind")
        entity_id = match.group("id")
        result = self.get_entity(entity_id)
        if isinstance(result, Exception):
          return result
        if not result.ok or result.entity is None:
          return result
        if result.entity.get("kind") != kind:
          return AtlasQueryResult(ok=False)
        return result

      return self.get_entity(stripped)
    except Exception as exc:  # noqa: BLE001
      return exc

  def _load_curated(self) -> list[EntityEnvelope] | Exception:
    return self._store.load_curated_entities()

  def _load_mappings(self) -> list[dict[str, Any]] | Exception:
    path = semantic_to_evidence_file(self._repo_root)
    if not path.is_file():
      return []
    try:
      loaded = load_yaml(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
      return exc
    if loaded is None:
      return []
    if not isinstance(loaded, dict):
      return ValueError(f"mappings file must be a YAML mapping: {path}")
    raw = loaded.get("mappings", [])
    if raw is None:
      return []
    if not isinstance(raw, list):
      return ValueError(f"mappings must be a list: {path}")
    return [item for item in raw if isinstance(item, dict)]

  def _load_evidence_index(self) -> dict[str, dict[str, Any]] | Exception:
    """Index generated evidence and derived summaries by id."""
    index: dict[str, dict[str, Any]] = {}
    for path, keys in (
      (symbols_file(self._repo_root), ("symbols",)),
      (verifications_file(self._repo_root), ("verifications", "tests")),
    ):
      if not path.is_file():
        continue
      try:
        loaded = load_yaml(path.read_text(encoding="utf-8"))
      except Exception as exc:  # noqa: BLE001
        return exc
      items = _list_from_payload(loaded, *keys)
      for item in items:
        if not isinstance(item, dict):
          continue
        evidence_id = item.get("id")
        if isinstance(evidence_id, str):
          index[evidence_id] = dict(item)

    entities_path = index_entities_file(self._repo_root)
    if entities_path.is_file():
      try:
        entries = json.loads(entities_path.read_text(encoding="utf-8"))
      except Exception as exc:  # noqa: BLE001
        return exc
      if isinstance(entries, list):
        for entry in entries:
          if not isinstance(entry, dict):
            continue
          evidence_id = entry.get("id")
          if isinstance(evidence_id, str) and evidence_id not in index:
            index[evidence_id] = dict(entry)
    return index


def _list_from_payload(payload: Any, *keys: str) -> list[Any]:
  if isinstance(payload, list):
    return payload
  if not isinstance(payload, dict):
    return []
  for key in keys:
    value = payload.get(key)
    if isinstance(value, list):
      return value
  return []


__all__ = [
  "AtlasQuery",
]

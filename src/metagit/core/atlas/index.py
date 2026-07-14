#!/usr/bin/env python
"""Rebuildable JSON entity index for Metagit Atlas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from metagit.core.atlas.models import EntityEnvelope
from metagit.core.atlas.paths import (
  generated_dir,
  index_dir,
  index_entities_file,
  intent_dir,
  inventory_file,
  ontology_dir,
  symbols_file,
  verifications_file,
)
from metagit.core.atlas.serialize import load_yaml


def _sort_key(entry: dict[str, Any]) -> str:
  return json.dumps(entry, sort_keys=True, separators=(",", ":"))


def _entity_summary(entity: EntityEnvelope) -> dict[str, Any]:
  return {
    "id": entity.metadata.id,
    "kind": entity.kind,
    "name": entity.metadata.name,
    "source": "curated",
  }


def _load_yaml_file(path: Path) -> Any | Exception:
  try:
    text = path.read_text(encoding="utf-8")
    return load_yaml(text)
  except Exception as exc:  # noqa: BLE001
    return exc


def _curated_entity_summaries(repo_root: Path) -> list[dict[str, Any]] | Exception:
  entries: list[dict[str, Any]] = []
  for root in (ontology_dir(repo_root), intent_dir(repo_root)):
    if not root.is_dir():
      continue
    for path in sorted(root.rglob("*.yaml")):
      loaded = _load_yaml_file(path)
      if isinstance(loaded, Exception):
        return loaded
      if not isinstance(loaded, dict):
        continue
      entities = loaded.get("entities")
      if not isinstance(entities, list):
        continue
      for item in entities:
        if not isinstance(item, dict):
          continue
        try:
          entity = EntityEnvelope.model_validate(item)
        except Exception as exc:  # noqa: BLE001
          return exc
        entries.append(_entity_summary(entity))
  return entries


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


def _generated_summaries(repo_root: Path) -> list[dict[str, Any]] | Exception:
  if not generated_dir(repo_root).is_dir():
    return []

  entries: list[dict[str, Any]] = []

  inv_path = inventory_file(repo_root)
  if inv_path.is_file():
    loaded = _load_yaml_file(inv_path)
    if isinstance(loaded, Exception):
      return loaded
    for item in _list_from_payload(loaded, "files"):
      if not isinstance(item, dict):
        continue
      path = item.get("path")
      if not isinstance(path, str):
        continue
      entries.append({
        "kind": "inventory",
        "path": path,
        "source": "generated",
      })

  sym_path = symbols_file(repo_root)
  if sym_path.is_file():
    loaded = _load_yaml_file(sym_path)
    if isinstance(loaded, Exception):
      return loaded
    for item in _list_from_payload(loaded, "symbols"):
      if not isinstance(item, dict):
        continue
      summary: dict[str, Any] = {
        "kind": str(item.get("kind", "symbol")),
        "source": "generated",
      }
      if isinstance(item.get("id"), str):
        summary["id"] = item["id"]
      if isinstance(item.get("locator"), str):
        summary["locator"] = item["locator"]
      entries.append(summary)

  ver_path = verifications_file(repo_root)
  if ver_path.is_file():
    loaded = _load_yaml_file(ver_path)
    if isinstance(loaded, Exception):
      return loaded
    for item in _list_from_payload(loaded, "verifications", "tests"):
      if not isinstance(item, dict):
        continue
      summary = {
        "kind": str(item.get("kind", "verification")),
        "source": "generated",
      }
      if isinstance(item.get("id"), str):
        summary["id"] = item["id"]
      if isinstance(item.get("locator"), str):
        summary["locator"] = item["locator"]
      entries.append(summary)

  return entries


def rebuild_entities_index(repo_root: str | Path) -> None | Exception:
  """Flatten curated + generated summaries into sorted ``entities.json``."""
  root = Path(repo_root)
  try:
    curated = _curated_entity_summaries(root)
    if isinstance(curated, Exception):
      return curated
    generated = _generated_summaries(root)
    if isinstance(generated, Exception):
      return generated

    entries = sorted([*curated, *generated], key=_sort_key)
    index_dir(root).mkdir(parents=True, exist_ok=True)
    payload = json.dumps(entries, indent=2, sort_keys=True) + "\n"
    index_entities_file(root).write_text(payload, encoding="utf-8")
    return None
  except Exception as exc:  # noqa: BLE001
    return exc


__all__ = [
  "rebuild_entities_index",
]

#!/usr/bin/env python
"""Atlas entity and config validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
from pydantic import BaseModel

from metagit.core.atlas.ids import validate_entity_id
from metagit.core.atlas.models import EntityEnvelope

_REF_LIST_KEYS = ("invariants", "contracts", "dependsOn")


def _schemas_dir() -> Path:
    """Return Atlas JSON Schema directory (packaged wheel or repo checkout).

    Installed wheels ship schemas under ``metagit/data/schemas/atlas/`` via
    ``package-data``. Repo checkouts also keep a docs/IDE copy at
    ``schemas/atlas/`` beside the package tree.
    """
    packaged = Path(__file__).resolve().parents[2] / "data" / "schemas" / "atlas"
    if packaged.is_dir():
        return packaged
    current = Path(__file__).resolve().parent
    for parent in (current, *current.parents):
        candidate = parent / "schemas" / "atlas"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("schemas/atlas directory not found")


def _load_schema(name: str) -> dict[str, Any]:
    path = _schemas_dir() / name
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class ValidationIssue(BaseModel):
    """Single validation finding for an Atlas entity or config."""

    code: str
    message: str
    entity_id: str | None = None


def _ref_lists_from_spec(spec: dict[str, Any]) -> list[tuple[str, list[str]]]:
    refs: list[tuple[str, list[str]]] = []
    for key in _REF_LIST_KEYS:
        value = spec.get(key)
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            refs.append((key, value))
    return refs


def validate_entities(entities: list[EntityEnvelope]) -> list[ValidationIssue]:
    """Validate cross-entity references and ID uniqueness."""
    issues: list[ValidationIssue] = []
    seen: dict[str, int] = {}
    id_set: set[str] = set()

    for entity in entities:
        entity_id = entity.metadata.id
        id_set.add(entity_id)

        try:
            validate_entity_id(entity_id)
        except ValueError as exc:
            issues.append(
                ValidationIssue(
                    code="invalid_id",
                    message=str(exc),
                    entity_id=entity_id,
                )
            )

        seen[entity_id] = seen.get(entity_id, 0) + 1

    for entity_id, count in seen.items():
        if count > 1:
            issues.append(
                ValidationIssue(
                    code="duplicate_id",
                    message=f"duplicate entity id {entity_id!r}",
                    entity_id=entity_id,
                )
            )

    for entity in entities:
        entity_id = entity.metadata.id
        for key, refs in _ref_lists_from_spec(entity.spec):
            for ref in refs:
                if ref not in id_set:
                    issues.append(
                        ValidationIssue(
                            code="dangling_ref",
                            message=f"dangling reference {ref!r} in spec.{key}",
                            entity_id=entity_id,
                        )
                    )

    return issues


def validate_config_dict(raw: dict[str, Any]) -> list[ValidationIssue]:
    """Validate a raw Atlas config dict against the JSON Schema."""
    schema = _load_schema("atlas-config.schema.json")
    validator = jsonschema.Draft202012Validator(schema)
    issues: list[ValidationIssue] = []
    for error in sorted(validator.iter_errors(raw), key=lambda item: list(item.absolute_path)):
        path = ".".join(str(part) for part in error.absolute_path)
        location = f" at {path}" if path else ""
        issues.append(
            ValidationIssue(
                code="schema_error",
                message=f"{error.message}{location}",
            )
        )
    return issues

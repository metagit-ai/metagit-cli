#!/usr/bin/env python
"""Atlas entity ID helpers."""

from __future__ import annotations

import re

_ID_RE = re.compile(r"^([a-z][a-z0-9_]*):([A-Za-z0-9_.\-]+)$")


def validate_entity_id(value: str) -> str:
  stripped = value.strip()
  if not _ID_RE.match(stripped):
    raise ValueError(
      f"invalid entity id {value!r}; expected kind:local (e.g. capability:payment.capture)"
    )
  return stripped


def parse_entity_id(value: str) -> tuple[str, str]:
  normalized = validate_entity_id(value)
  kind, local = normalized.split(":", 1)
  return kind, local


def normalize_entity_id(value: str) -> str:
  stripped = value.strip()
  if ":" not in stripped:
    raise ValueError(f"invalid entity id {value!r}")
  kind, local = stripped.split(":", 1)
  return validate_entity_id(f"{kind.lower()}:{local}")

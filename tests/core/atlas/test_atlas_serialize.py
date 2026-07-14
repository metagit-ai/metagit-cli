#!/usr/bin/env python
"""Unit tests for deterministic Atlas YAML serialization."""

from __future__ import annotations

from metagit.core.atlas.serialize import dump_yaml, load_yaml


def test_dump_is_stable_for_same_mapping() -> None:
  payload = {"b": 2, "a": {"z": 1, "y": 2}}
  first = dump_yaml(payload)
  second = dump_yaml(payload)
  assert first == second
  assert "a:" in first
  loaded = load_yaml(first)
  assert loaded["b"] == 2

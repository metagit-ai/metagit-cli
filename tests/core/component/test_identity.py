#!/usr/bin/env python
"""Tests for component identity helpers."""

from __future__ import annotations

from metagit.core.component.identity import component_id, parse_component_id


def test_component_id_joins_three_segments() -> None:
  assert component_id("acme", "platform", "web") == "acme/platform/web"


def test_parse_component_id_roundtrip() -> None:
  parsed = parse_component_id("acme/platform/web")
  assert not isinstance(parsed, Exception)
  assert parsed.project == "acme"
  assert parsed.repo == "platform"
  assert parsed.component == "web"
  assert parsed.key == "acme/platform/web"


def test_parse_component_id_rejects_wrong_arity() -> None:
  two = parse_component_id("acme/web")
  four = parse_component_id("ws/acme/platform/web")
  assert isinstance(two, ValueError)
  assert isinstance(four, ValueError)


def test_parse_component_id_rejects_empty_segments() -> None:
  assert isinstance(parse_component_id("acme//web"), ValueError)
  assert isinstance(parse_component_id("/platform/web"), ValueError)


def test_component_id_rejects_slash_in_parts() -> None:
  assert isinstance(component_id("acme/x", "platform", "web"), ValueError)

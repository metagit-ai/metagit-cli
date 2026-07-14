#!/usr/bin/env python
"""Unit tests for Atlas ID helpers."""

from __future__ import annotations

import pytest

from metagit.core.atlas.ids import normalize_entity_id, parse_entity_id, validate_entity_id


def test_validate_accepts_capability_id() -> None:
  assert validate_entity_id("capability:payment.capture") == "capability:payment.capture"


def test_validate_rejects_spaces() -> None:
  with pytest.raises(ValueError):
    validate_entity_id("capability:bad id")


def test_parse_splits_kind_and_local() -> None:
  kind, local = parse_entity_id("invariant:refund.idempotent")
  assert kind == "invariant"
  assert local == "refund.idempotent"


def test_normalize_strips_and_lowercases_kind() -> None:
  assert normalize_entity_id("Capability:Payment.Capture") == "capability:Payment.Capture"

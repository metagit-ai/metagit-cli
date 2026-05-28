#!/usr/bin/env python
"""Tests for manifest gate idempotency helpers."""

from pathlib import Path

import yaml

from metagit.core.config.manifest_gate import (
    ManifestGateInvalid,
    ManifestGateOutcome,
    evaluate_existing_manifest,
)


def test_evaluate_missing_manifest(tmp_path: Path) -> None:
  target = tmp_path / ".metagit.yml"
  assert evaluate_existing_manifest(target) is None


def test_evaluate_valid_existing_manifest(tmp_path: Path) -> None:
  target = tmp_path / ".metagit.yml"
  target.write_text(
    yaml.dump({"name": "demo", "kind": "application"}),
    encoding="utf-8",
  )
  gate = evaluate_existing_manifest(target)
  assert isinstance(gate, ManifestGateOutcome)
  assert gate.action == "exists_valid"
  assert gate.path == target


def test_evaluate_invalid_existing_manifest(tmp_path: Path) -> None:
  target = tmp_path / ".metagit.yml"
  target.write_text("name: demo\nkind: not-a-kind\n", encoding="utf-8")
  gate = evaluate_existing_manifest(target)
  assert isinstance(gate, ManifestGateInvalid)


def test_evaluate_force_skips_existing(tmp_path: Path) -> None:
  target = tmp_path / ".metagit.yml"
  target.write_text(
    yaml.dump({"name": "demo", "kind": "application"}),
    encoding="utf-8",
  )
  assert evaluate_existing_manifest(target, force=True) is None

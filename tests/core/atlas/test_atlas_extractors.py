#!/usr/bin/env python
"""Unit tests for Atlas extractors."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from metagit.core.atlas.extractors.inventory import build_inventory
from metagit.core.atlas.extractors.python_ast import extract_python_symbols
from metagit.core.atlas.extractors.tests_discovery import discover_tests

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "atlas" / "python_toy"


@pytest.fixture()
def toy_repo(tmp_path: Path) -> Path:
  dest = tmp_path / "python_toy"
  shutil.copytree(FIXTURE, dest)
  return dest


def test_inventory_lists_python_and_skips_env(toy_repo: Path) -> None:
  inv = build_inventory(toy_repo, revision="deadbeef")
  paths = {item["path"] for item in inv["files"]}
  assert "src/toy/refunds.py" in paths
  assert ".env" not in paths
  assert inv["provenance"]["extractor"].startswith("inventory@")


def test_python_symbols_include_refund_service(toy_repo: Path) -> None:
  symbols = extract_python_symbols(toy_repo, revision="deadbeef")
  locators = {s["locator"] for s in symbols}
  assert any("RefundService.issue" in loc for loc in locators)
  assert all("confidence" in s for s in symbols)


def test_discover_tests_finds_idempotent(toy_repo: Path) -> None:
  tests = discover_tests(toy_repo, revision="deadbeef")
  assert any("test_issue_idempotent" in t.get("locator", t.get("id", "")) for t in tests)

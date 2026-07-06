#!/usr/bin/env python
"""Tests for campaigns root resolution."""

from __future__ import annotations

from pathlib import Path

from metagit.core.workspace.root_resolver import (
    DEFAULT_CAMPAIGNS_PATH,
    resolve_campaigns_root,
)


def test_resolve_campaigns_root_default(tmp_path: Path) -> None:
    root = resolve_campaigns_root(str(tmp_path))
    assert root == str((tmp_path / DEFAULT_CAMPAIGNS_PATH).resolve())


def test_resolve_campaigns_root_custom_relative(tmp_path: Path) -> None:
    root = resolve_campaigns_root(str(tmp_path), "knowledge/campaigns")
    assert root == str((tmp_path / "knowledge" / "campaigns").resolve())


def test_resolve_campaigns_root_absolute(tmp_path: Path) -> None:
    absolute = tmp_path / "custom-campaigns"
    root = resolve_campaigns_root(str(tmp_path), str(absolute))
    assert root == str(absolute.resolve())

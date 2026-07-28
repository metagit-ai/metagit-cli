#!/usr/bin/env python
"""Tests for workspace sync-root resolution against a targeted manifest."""

from __future__ import annotations

from pathlib import Path

from metagit.core.workspace.root_resolver import resolve_workspace_root


def test_resolve_workspace_root_homes_relative_path_to_manifest_dir(tmp_path: Path) -> None:
    umbrella = tmp_path / "umbrella"
    umbrella.mkdir()
    manifest = umbrella / ".metagit.yml"
    manifest.write_text("name: demo\nkind: umbrella\n", encoding="utf-8")
    sync = umbrella / ".metagit"
    sync.mkdir()

    root = resolve_workspace_root(str(manifest), "./.metagit")
    assert root == str(sync.resolve())


def test_resolve_workspace_root_override_wins(tmp_path: Path) -> None:
    umbrella = tmp_path / "umbrella"
    umbrella.mkdir()
    manifest = umbrella / ".metagit.yml"
    manifest.write_text("name: demo\nkind: umbrella\n", encoding="utf-8")
    other = tmp_path / "other-sync"
    other.mkdir()

    root = resolve_workspace_root(str(manifest), "./.metagit", override=str(other))
    assert root == str(other.resolve())


def test_resolve_workspace_root_keeps_absolute_workspace_path(tmp_path: Path) -> None:
    umbrella = tmp_path / "umbrella"
    umbrella.mkdir()
    manifest = umbrella / ".metagit.yml"
    manifest.write_text("name: demo\nkind: umbrella\n", encoding="utf-8")
    absolute = tmp_path / "absolute-sync"
    absolute.mkdir()

    root = resolve_workspace_root(str(manifest), str(absolute))
    assert root == str(absolute.resolve())

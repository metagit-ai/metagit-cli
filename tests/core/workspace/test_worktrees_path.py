#!/usr/bin/env python
"""Tests for worktrees path resolution and reserved project names."""

from __future__ import annotations

from pathlib import Path

from metagit.core.coordination.paths import worktree_checkout_path
from metagit.core.workspace.layout_resolver import validate_layout_name
from metagit.core.workspace.root_resolver import (
    reserved_project_names,
    resolve_worktrees_root,
)


def test_resolve_worktrees_root_default(tmp_path: Path) -> None:
    root = resolve_worktrees_root(str(tmp_path))
    assert Path(root) == (tmp_path / ".worktrees").resolve()


def test_resolve_worktrees_root_custom_relative(tmp_path: Path) -> None:
    root = resolve_worktrees_root(str(tmp_path), "agent-worktrees")
    assert Path(root) == (tmp_path / "agent-worktrees").resolve()


def test_worktree_checkout_uses_configured_path(tmp_path: Path) -> None:
    path = worktree_checkout_path(
        str(tmp_path),
        "agent-1",
        "demo",
        "service-a",
        worktrees_path="wt",
    )
    assert path == tmp_path / "wt" / "agent-1" / "demo" / "service-a"


def test_reserved_project_names_include_worktrees_and_campaigns() -> None:
    names = reserved_project_names()
    assert "worktrees" in names
    assert ".worktrees" in names
    assert "campaigns" in names
    assert "_campaigns" in names


def test_validate_layout_name_blocks_reserved_project() -> None:
    reserved = reserved_project_names()
    assert validate_layout_name("worktrees", label="project name", reserved=reserved)
    assert validate_layout_name("campaigns", label="project name", reserved=reserved)
    assert validate_layout_name("ok-project", label="project name", reserved=reserved) is None

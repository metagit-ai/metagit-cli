#!/usr/bin/env python
"""Tests for repository-relative component path normalization."""

from __future__ import annotations

from metagit.core.component.paths import normalize_repo_relative_path


def test_normalize_dot_is_repo_root() -> None:
  assert normalize_repo_relative_path(".") == "."
  assert normalize_repo_relative_path("./") == "."


def test_normalize_collapses_separators_and_dot_segments() -> None:
  result = normalize_repo_relative_path("apps//web/./src")
  assert result == "apps/web/src"


def test_normalize_windows_separators() -> None:
  assert normalize_repo_relative_path("apps\\web") == "apps/web"


def test_normalize_rejects_absolute_posix() -> None:
  assert isinstance(normalize_repo_relative_path("/apps/web"), ValueError)


def test_normalize_rejects_escape() -> None:
  assert isinstance(normalize_repo_relative_path("../other"), ValueError)
  assert isinstance(normalize_repo_relative_path("apps/../../other"), ValueError)


def test_normalize_allows_internal_dotdot_that_stays_inside() -> None:
  assert normalize_repo_relative_path("apps/web/../api") == "apps/api"


def test_normalize_rejects_empty() -> None:
  assert isinstance(normalize_repo_relative_path("  "), ValueError)

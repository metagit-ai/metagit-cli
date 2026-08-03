#!/usr/bin/env python
"""Unit tests for interactive project name picker."""

from __future__ import annotations

from metagit.core.project import project_picker


def test_select_project_name_empty_list_returns_error() -> None:
  result = project_picker.select_project_name([])
  assert isinstance(result, ValueError)


def test_select_project_name_returns_finder_selection(monkeypatch) -> None:
  class _FakeFinder:
    def __init__(self, config) -> None:
      self.config = config

    def run(self):
      return "platform"

  monkeypatch.setattr(project_picker, "FuzzyFinder", _FakeFinder)
  result = project_picker.select_project_name(["platform", "edge"])
  assert result == "platform"


def test_select_project_name_none_on_cancel(monkeypatch) -> None:
  class _FakeFinder:
    def __init__(self, _config) -> None:
      pass

    def run(self):
      return None

  monkeypatch.setattr(project_picker, "FuzzyFinder", _FakeFinder)
  assert project_picker.select_project_name(["a", "b"]) is None

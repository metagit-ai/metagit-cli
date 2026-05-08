#!/usr/bin/env python
"""
Unit tests for skills installer helpers.
"""

from metagit.core.skills.installer import autodetect_targets, resolve_targets


def test_resolve_targets_respects_disable() -> None:
    targets = resolve_targets(
        mode="skills",
        scope="project",
        enable_targets=["opencode", "hermes"],
        disable_targets=["hermes"],
    )
    assert targets == ["opencode"]


def test_autodetect_targets_project_scope(monkeypatch, tmp_path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".opencode").mkdir()
    monkeypatch.chdir(project_root)
    detected = autodetect_targets(mode="skills", scope="project")
    assert "opencode" in detected

#!/usr/bin/env python
"""Tests for unmanaged sync directory listing and prune helpers."""

from pathlib import Path

from metagit.core.config.models import MetagitConfig
from metagit.core.project.manager import ProjectManager
from metagit.core.project.models import ProjectPath
from metagit.core.workspace.models import Workspace, WorkspaceProject


class _DummyLogger:
    def set_level(self, _: str) -> None:
        return

    def warning(self, _: str) -> None:
        return

    def debug(self, _: str) -> None:
        return


def _config_one_repo() -> MetagitConfig:
    return MetagitConfig(
        name="cfg",
        workspace=Workspace(
            projects=[
                WorkspaceProject(
                    name="platform",
                    repos=[
                        ProjectPath(
                            name="managed",
                            url="https://example.com/managed.git",
                        )
                    ],
                )
            ]
        ),
    )


def test_list_unmanaged_sync_directories_excludes_managed(tmp_path: Path) -> None:
    workspace_root = tmp_path / ".metagit"
    proj = workspace_root / "platform"
    proj.mkdir(parents=True)
    (proj / "managed").mkdir()
    (proj / "orphan-dir").mkdir()

    mgr = ProjectManager(workspace_root, _DummyLogger())
    unmanaged = mgr.list_unmanaged_sync_directories(
        _config_one_repo(), "platform", ignore_hidden=True
    )
    assert [p.name for p in unmanaged] == ["orphan-dir"]


def test_list_unmanaged_respects_dot_directories_when_ignore_hidden(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / ".metagit"
    proj = workspace_root / "platform"
    proj.mkdir(parents=True)
    (proj / "managed").mkdir()
    (proj / ".cache").mkdir()
    (proj / "orphan-dir").mkdir()

    mgr = ProjectManager(workspace_root, _DummyLogger())
    hidden_on = mgr.list_unmanaged_sync_directories(
        _config_one_repo(), "platform", ignore_hidden=True
    )
    assert [p.name for p in hidden_on] == ["orphan-dir"]

    hidden_off = mgr.list_unmanaged_sync_directories(
        _config_one_repo(), "platform", ignore_hidden=False
    )
    assert sorted(p.name for p in hidden_off) == [".cache", "orphan-dir"]


def test_select_repo_skips_dot_directories_when_ignore_hidden(
    tmp_path: Path, monkeypatch
) -> None:
    """Dot-directories should not appear in the fuzzy finder when ignore_hidden is true."""
    workspace_root = tmp_path / ".metagit"
    project_root = workspace_root / "platform"
    project_root.mkdir(parents=True)
    (project_root / "managed").mkdir()
    (project_root / ".venv").mkdir()

    captured: dict = {}

    class _DummyFinder:
        def __init__(self, config) -> None:
            captured["config"] = config

        def run(self):
            return None

    monkeypatch.setattr("metagit.core.project.manager.FuzzyFinder", _DummyFinder)

    mgr = ProjectManager(workspace_root, _DummyLogger())
    _ = mgr.select_repo(
        _config_one_repo(),
        "platform",
        show_preview=False,
        ignore_hidden=True,
    )
    names = [item.name for item in captured["config"].items]
    assert ".venv" not in names
    assert "managed" in names

#!/usr/bin/env python
"""Tests for in-process TUI repo picker."""

from pathlib import Path

from metagit.core.tui.catalog import build_command_catalog
from metagit.core.tui.repo_picker import run_repo_picker_session


def test_workspace_select_catalog_action_is_interactive() -> None:
    action = next(
        item for section in build_command_catalog() for item in section.actions if item.id == "workspace-select"
    )
    assert action.interactive is True


def test_run_repo_picker_session_without_manifest(tmp_path: Path, capsys) -> None:
    app_cfg = tmp_path / "metagit.config.yaml"
    app_cfg.write_text("config:\n  description: test\n",encoding="utf-8")
    result = run_repo_picker_session(
        app_config_path=str(app_cfg),
        manifest_path=None,
    )
    captured = capsys.readouterr()
    assert result is None
    assert ".metagit.yml" in captured.err


def test_run_repo_picker_session_selects_and_opens_editor(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    workspace = tmp_path / ".metagit"
    platform = workspace / "platform" / "backend"
    platform.mkdir(parents=True)

    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(
        "\n".join(
            [
                "name: test",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: platform",
                "      repos:",
                "        - name: backend",
                "          url: https://example.com/backend.git",
            ]
        )
        + "\n",
       encoding="utf-8",
    )
    app_cfg = tmp_path / "metagit.config.yaml"
    app_cfg.write_text(
        "\n".join(
            [
                "config:",
                "  description: test",
                "  editor: echo",
                "  workspace:",
                f"    path: {workspace.as_posix()}",
                "    default_project: platform",
            ]
        )
        + "\n",
       encoding="utf-8",
    )

    repo_path = str((workspace / "platform" / "backend").resolve())

    class _DummyManager:
        def resolve_selected_repo_path(self, *_args, **_kwargs):
            return repo_path

        def select_repo(self, *_args, **_kwargs):
            return repo_path

    monkeypatch.setattr(
        "metagit.core.tui.repo_picker.project_manager_from_app",
        lambda *_args, **_kwargs: _DummyManager(),
    )
    opened: list[str] = []

    def _fake_open_editor(editor: str, path: str):
        opened.append(path)
        return None

    monkeypatch.setattr("metagit.core.tui.repo_picker.open_editor", _fake_open_editor)

    selected = run_repo_picker_session(
        app_config_path=str(app_cfg),
        manifest_path=str(manifest),
        repo_name="backend",
    )
    captured = capsys.readouterr()
    assert selected == repo_path
    assert opened == [repo_path]
    assert "Selected repo:" in captured.out

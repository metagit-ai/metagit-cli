#!/usr/bin/env python
"""Tests for Metagit CLI shell completion helpers."""

from __future__ import annotations

from pathlib import Path

import click
import pytest
import yaml

from metagit.cli.shell_completion import (
    complete_projects,
    complete_repos,
    complete_repomix_profiles,
    default_install_path,
    render_completion_script,
    verify_completion_callback,
)
from metagit.cli.main import cli


def _write_manifest(tmp_path: Path) -> Path:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "name": "demo",
                "kind": "application",
                "workspace": {
                    "projects": [
                        {
                            "name": "platform",
                            "repos": [
                                {"name": "api", "url": "https://example.com/api.git"},
                                {"name": "web", "path": "platform/web"},
                            ],
                        },
                        {"name": "infra", "repos": []},
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    return manifest


def test_complete_projects_from_manifest(tmp_path: Path, monkeypatch) -> None:
    manifest = _write_manifest(tmp_path)
    monkeypatch.chdir(tmp_path)

    @click.command()
    @click.option("--definition", "-c", "definition_path", default=".metagit.yml")
    @click.option("--project", shell_complete=complete_projects)
    def _cmd(definition_path: str, project: str) -> None:
        _ = (definition_path, project)

    ctx = click.Context(_cmd)
    ctx.params = {"definition_path": str(manifest)}
    project_param = next(param for param in _cmd.params if param.name == "project")
    items = complete_projects(ctx, project_param, "plat")
    assert [item.value for item in items] == ["platform"]


def test_complete_repos_scoped_to_project(tmp_path: Path, monkeypatch) -> None:
    manifest = _write_manifest(tmp_path)
    monkeypatch.chdir(tmp_path)

    @click.command()
    @click.option("--definition", "-c", "definition_path", default=".metagit.yml")
    @click.option("--project", "project_name")
    @click.option("--repo", shell_complete=complete_repos)
    def _cmd(definition_path: str, project_name: str, repo: str) -> None:
        _ = (definition_path, project_name, repo)

    ctx = click.Context(_cmd)
    ctx.params = {
        "definition_path": str(manifest),
        "project_name": "platform",
    }
    repo_param = next(param for param in _cmd.params if param.name == "repo")
    items = complete_repos(ctx, repo_param, "a")
    assert {item.value for item in items} == {"api"}


def test_complete_repomix_profiles_includes_bundled_names() -> None:
    ctx = click.Context(click.Command("noop"))
    items = complete_repomix_profiles(ctx, click.Argument("x"), "bug")
    values = {item.value for item in items}
    assert "bugfix-local" in values


def test_render_zsh_completion_script() -> None:
    script = render_completion_script(cli, shell_name="zsh")
    assert "#compdef metagit" in script
    assert "_metagit_completion" in script


def test_default_install_path_zsh() -> None:
    path = default_install_path("zsh")
    assert path.name == "_metagit"
    assert ".zfunc" in str(path)


def test_verify_completion_callback(monkeypatch) -> None:
    monkeypatch.setenv("_METAGIT_COMPLETE", "zsh_source")
    ok, detail = verify_completion_callback()
    assert ok, detail


def test_main_honors_metagit_complete_with_windows_prog_name(monkeypatch) -> None:
    """Regression: Click must not derive ``_METAGIT_EXE_COMPLETE`` on Windows."""
    import sys

    from metagit.cli.main import main

    monkeypatch.delenv("_METAGIT_EXE_COMPLETE", raising=False)
    monkeypatch.setenv("_METAGIT_COMPLETE", "zsh_source")
    monkeypatch.setattr(sys, "argv", [r"C:\venv\Scripts\metagit.exe"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0

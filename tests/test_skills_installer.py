#!/usr/bin/env python
"""
Unit tests for skills installer helpers.
"""

import json
from pathlib import Path

import pytest

from metagit.core.skills.installer import (
    autodetect_targets,
    install_mcp_for_targets,
    install_skills_for_targets,
    resolve_project_install_root,
    resolve_skill_names,
    resolve_targets,
)


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


def test_resolve_skill_names_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown skill"):
        resolve_skill_names(["not-a-real-skill"])


def test_install_skills_for_targets_single_skill(monkeypatch, tmp_path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".opencode").mkdir()
    monkeypatch.chdir(project_root)
    results = install_skills_for_targets(
        targets=["opencode"],
        scope="project",
        skill_names=["metagit-gitnexus"],
    )
    destination = project_root / ".opencode" / "skills"
    assert results[0].applied is True
    assert "metagit-gitnexus" in results[0].details
    installed = [p.name for p in destination.iterdir() if p.is_dir()]
    assert installed == ["metagit-gitnexus"]


def test_install_skills_dry_run_writes_nothing(monkeypatch, tmp_path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".opencode").mkdir()
    monkeypatch.chdir(project_root)
    results = install_skills_for_targets(
        targets=["opencode"],
        scope="project",
        skill_names=["metagit-gitnexus"],
        dry_run=True,
    )
    destination = project_root / ".opencode" / "skills"
    assert results[0].dry_run is True
    assert results[0].details.startswith("Would install")
    assert not destination.exists()


def test_resolve_project_install_root_prefers_git_toplevel(
    monkeypatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    nested = repo / "src" / "pkg"
    nested.mkdir(parents=True)
    (repo / ".git").mkdir()
    monkeypatch.chdir(nested)
    assert resolve_project_install_root() == repo.resolve()


def test_install_skills_project_scope_uses_explicit_project_root(
    monkeypatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    nested = repo / "src"
    nested.mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / ".opencode").mkdir()
    monkeypatch.chdir(nested)
    results = install_skills_for_targets(
        targets=["opencode"],
        scope="project",
        skill_names=["metagit-gitnexus"],
        project_root=resolve_project_install_root(),
    )
    destination = repo / ".opencode" / "skills"
    assert results[0].applied is True
    assert destination.exists()
    assert (destination / "metagit-gitnexus").is_dir()
    assert not (nested / ".opencode").exists()


def test_hermes_user_skills_honor_hermes_home(monkeypatch, tmp_path: Path) -> None:
    hermes_home = tmp_path / "custom-hermes"
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    results = install_skills_for_targets(
        targets=["hermes"],
        scope="user",
        skill_names=["metagit-cli"],
    )
    destination = hermes_home / "skills"
    assert results[0].applied is True
    assert results[0].path == str(destination)
    assert (destination / "metagit-cli").is_dir()


def test_hermes_mcp_writes_config_yaml_with_metagit_binary(
    monkeypatch, tmp_path: Path
) -> None:
    hermes_home = tmp_path / "custom-hermes"
    hermes_home.mkdir()
    existing = hermes_home / "config.yaml"
    existing.write_text("model: demo\nmcp_servers: {}\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    fake_metagit = str((tmp_path / "bin" / "metagit").resolve())
    monkeypatch.setattr(
        "metagit.core.skills.installer.shutil.which",
        lambda name: fake_metagit if name == "metagit" else None,
    )

    results = install_mcp_for_targets(targets=["hermes"], scope="user")
    assert results[0].applied is True
    assert results[0].path == str(hermes_home / "config.yaml")
    content = (hermes_home / "config.yaml").read_text(encoding="utf-8")
    assert "mcp_servers:" in content
    assert "metagit:" in content
    assert "uvx" not in content
    assert fake_metagit in content
    assert "args:" in content
    assert "- mcp" in content
    assert "- serve" in content
    assert "METAGIT_AGENT_MODE" in content
    assert "model: demo" in content


def test_json_mcp_uses_metagit_binary_not_uvx(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    monkeypatch.chdir(project)
    fake_metagit = str((tmp_path / "bin" / "metagit").resolve())
    monkeypatch.setattr(
        "metagit.core.skills.installer.shutil.which",
        lambda name: fake_metagit if name == "metagit" else None,
    )

    results = install_mcp_for_targets(targets=["opencode"], scope="project")
    assert results[0].applied is True
    config = json.loads((project / ".opencode" / "mcp.json").read_text(encoding="utf-8"))
    entry = config["mcpServers"]["metagit"]
    assert entry["command"] == fake_metagit
    assert entry["args"] == ["mcp", "serve"]
    assert "uvx" not in entry["command"]

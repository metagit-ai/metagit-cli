#!/usr/bin/env python
"""Unit tests for RepoPromoteService."""

from __future__ import annotations

import os
from pathlib import Path

from git import Repo

from metagit.core.config.models import MetagitConfig
from metagit.core.project.manager import ProjectManager
from metagit.core.project.repo_promote_service import (
    RepoPromoteService,
    resolve_git_remote_url,
)


class _DummyLogger:
    def set_level(self, _: str) -> None:
        return

    def warning(self, _: str) -> None:
        return

    def debug(self, _: str) -> None:
        return

    def info(self, _: str) -> None:
        return


def _write_manifest(path: Path, *, project: str, repo_name: str, repo_path: str) -> None:
    path.write_text(
        "\n".join(
            [
                "name: test",
                "kind: application",
                "workspace:",
                "  projects:",
                f"    - name: {project}",
                "      repos:",
                f"        - name: {repo_name}",
                f"          path: {repo_path.replace(os.sep, '/')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _init_local_git_repo(path: Path, *, remote_url: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(path)
    readme = path / "README.md"
    readme.write_text("hello", encoding="utf-8")
    repo.index.add([str(readme.relative_to(path))])
    repo.index.commit("init")
    repo.create_remote("origin", remote_url)


def _load_config(config_path: Path) -> MetagitConfig:
    from metagit.core.config.manager import MetagitConfigManager

    manager = MetagitConfigManager(config_path=str(config_path))
    loaded = manager.load_config()
    assert not isinstance(loaded, Exception)
    return loaded


def test_resolve_git_remote_url_reads_origin(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _init_local_git_repo(
        source,
        remote_url="https://github.com/example-org/example.git",
    )
    assert (
        resolve_git_remote_url(source)
        == "https://github.com/example-org/example.git"
    )


def test_promote_dry_run_reports_plan(tmp_path: Path) -> None:
    source = tmp_path / "user-repo"
    _init_local_git_repo(
        source,
        remote_url="https://github.com/example-org/example.git",
    )
    workspace_root = tmp_path / ".metagit"
    config_path = tmp_path / ".metagit.yml"
    _write_manifest(
        config_path,
        project="platform",
        repo_name="example",
        repo_path=str(source),
    )
    config = _load_config(config_path)
    manager = ProjectManager(workspace_root, _DummyLogger())

    result = RepoPromoteService().promote(
        config,
        str(config_path),
        workspace_root=str(workspace_root),
        project_name="platform",
        repo_name="example",
        project_manager=manager,
        dry_run=True,
    )

    assert result.ok is True
    assert result.dry_run is True
    assert result.url == "https://github.com/example-org/example.git"
    assert result.manifest_updated is False


def test_promote_updates_manifest_and_clones(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "user-repo"
    remote_url = "https://github.com/example-org/example.git"
    _init_local_git_repo(source, remote_url=remote_url)

    workspace_root = tmp_path / ".metagit"
    platform_dir = workspace_root / "platform"
    platform_dir.mkdir(parents=True)
    mount = platform_dir / "example"
    os.symlink(source, mount, target_is_directory=True)

    config_path = tmp_path / ".metagit.yml"
    _write_manifest(
        config_path,
        project="platform",
        repo_name="example",
        repo_path=str(source),
    )
    config = _load_config(config_path)
    manager = ProjectManager(workspace_root, _DummyLogger())

    def _fake_clone(url: str, target: str, progress=None) -> None:  # noqa: ARG001
        os.makedirs(target, exist_ok=True)
        Path(target, ".git").mkdir(exist_ok=True)
        Path(target, "README.md").write_text("cloned", encoding="utf-8")

    monkeypatch.setattr(
        "metagit.core.project.manager.git.Repo.clone_from",
        _fake_clone,
    )

    result = RepoPromoteService().promote(
        config,
        str(config_path),
        workspace_root=str(workspace_root),
        project_name="platform",
        repo_name="example",
        project_manager=manager,
    )

    assert result.ok is True
    assert result.manifest_updated is True
    assert result.mount_removed is True
    assert result.synced is True
    assert mount.is_dir()
    assert not mount.is_symlink()
    assert (mount / "README.md").read_text(encoding="utf-8") == "cloned"

    reloaded = _load_config(config_path)
    project = reloaded.workspace.projects[0]
    repo_entry = project.repos[0]
    assert repo_entry.path is None
    assert str(repo_entry.url) == remote_url


def test_promote_rejects_non_local_entry(tmp_path: Path) -> None:
    config_path = tmp_path / ".metagit.yml"
    config_path.write_text(
        "\n".join(
            [
                "name: test",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: platform",
                "      repos:",
                "        - name: example",
                "          url: https://github.com/example-org/example.git",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    config = _load_config(config_path)
    manager = ProjectManager(tmp_path / ".metagit", _DummyLogger())

    result = RepoPromoteService().promote(
        config,
        str(config_path),
        workspace_root=str(tmp_path / ".metagit"),
        project_name="platform",
        repo_name="example",
        project_manager=manager,
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error.kind == "not_local_path"

#!/usr/bin/env python
"""
Unit tests for metagit.core.mcp.root_resolver
"""

from pathlib import Path

from metagit.core.mcp.root_resolver import WorkspaceRootResolver


def test_env_root_has_highest_precedence(monkeypatch, tmp_path: Path) -> None:
    env_root = tmp_path / "env-root"
    env_root.mkdir()
    monkeypatch.setenv("METAGIT_WORKSPACE_ROOT", str(env_root))
    resolver = WorkspaceRootResolver()

    result = resolver.resolve(cwd=str(tmp_path), cli_root=str(tmp_path / "cli-root"))

    assert result == str(env_root.resolve())


def test_cli_root_used_when_env_unset(monkeypatch, tmp_path: Path) -> None:
    cli_root = tmp_path / "cli-root"
    cli_root.mkdir()
    monkeypatch.delenv("METAGIT_WORKSPACE_ROOT", raising=False)
    resolver = WorkspaceRootResolver()

    result = resolver.resolve(cwd=str(tmp_path), cli_root=str(cli_root))

    assert result == str(cli_root.resolve())


def test_walk_up_finds_workspace_root(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("METAGIT_WORKSPACE_ROOT", raising=False)
    root = tmp_path / "workspace-root"
    nested = root / "services" / "api"
    nested.mkdir(parents=True)
    (root / ".metagit.yml").write_text("name: test\nkind: application\n", encoding="utf-8")
    resolver = WorkspaceRootResolver()

    result = resolver.resolve(cwd=str(nested), cli_root=None)

    assert result == str(root.resolve())

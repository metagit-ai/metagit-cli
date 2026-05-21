#!/usr/bin/env python
"""CLI tests for metagit context pack and repo-card."""

import os
from pathlib import Path

from click.testing import CliRunner
from git import Repo

from metagit.cli.main import cli


def _env_workspace_root(root: Path) -> dict[str, str]:
    workspace = str(root.resolve())
    return {**os.environ, "METAGIT_WORKSPACE_PATH": workspace}


def test_context_pack_tier_zero_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_workspace(tmp_path, with_git_repo=False)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["context", "pack", "--tier", "0", "--json"],
        env=_env_workspace_root(tmp_path),
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert '"tier": 0' in result.output
    assert '"workspace_name": "ctx-cli"' in result.output


def test_context_pack_tier_one_human_summary(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_workspace(tmp_path, with_git_repo=True)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "context",
            "pack",
            "--tier",
            "1",
            "--project",
            "demo",
            "--repo",
            "svc",
        ],
        env=_env_workspace_root(tmp_path),
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "tier: 1" in result.output
    assert "cards: 1 repo card(s)" in result.output
    assert "demo/svc:" in result.output


def test_context_repo_card_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_workspace(tmp_path, with_git_repo=True)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "context",
            "repo-card",
            "--project",
            "demo",
            "--repo",
            "svc",
            "--json",
        ],
        env=_env_workspace_root(tmp_path),
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert '"tier": 1' in result.output
    assert '"repo_name": "svc"' in result.output


def test_context_repo_card_unknown_repo_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_workspace(tmp_path, with_git_repo=True)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "context",
            "repo-card",
            "--project",
            "demo",
            "--repo",
            "nope",
            "--json",
        ],
        env=_env_workspace_root(tmp_path),
        catch_exceptions=False,
    )
    assert result.exit_code != 0


def _write_workspace(root: Path, *, with_git_repo: bool) -> None:
    (root / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: ctx-cli",
                "kind: application",
                "workspace:",
                "  projects:",
                "    - name: demo",
                "      repos:",
                "        - name: svc",
                "          path: demo/svc",
                "          sync: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    svc = root / "demo" / "svc"
    svc.mkdir(parents=True)
    if with_git_repo:
        Repo.init(svc)
        (svc / "README.md").write_text("# svc\n", encoding="utf-8")

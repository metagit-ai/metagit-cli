#!/usr/bin/env python
"""CLI smoke tests for ACL command groups."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner
from git import Repo

from metagit.cli.main import cli


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(str(path))
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("init")


def test_branch_lease_cli_json(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _init_repo(tmp_path / "demo" / "service-a")
    runner = CliRunner()
    allocate = runner.invoke(
        cli,
        [
            "branch",
            "allocate",
            "--definition",
            str(tmp_path / ".metagit.yml"),
            "--repository",
            "demo/service-a",
            "--agent-id",
            "agent-1",
            "--task-id",
            "412",
            "--json",
        ],
        obj={"config_path": None},
    )
    assert allocate.exit_code == 0, allocate.output
    assert "agent/412" in allocate.output

    lease = runner.invoke(
        cli,
        [
            "lease",
            "acquire",
            "--definition",
            str(tmp_path / ".metagit.yml"),
            "--repository",
            "demo/service-a",
            "--agent-id",
            "agent-1",
            "--task-id",
            "412",
            "--branch",
            "agent/412",
            "--json",
        ],
        obj={"config_path": None},
    )
    assert lease.exit_code == 0, lease.output
    assert "lease_id" in lease.output

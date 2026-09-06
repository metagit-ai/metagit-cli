#!/usr/bin/env python
"""CLI smoke tests for ACL command groups."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from git import Repo

from metagit.cli.main import cli

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "components"
NATIVE = FIXTURES / "native-nested.yml"


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


def test_claim_declare_component_web_defaults_patterns(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    definition = tmp_path / ".metagit.yml"
    definition.write_text(NATIVE.read_text(encoding="utf-8"), encoding="utf-8")
    runner = CliRunner()
    declared = runner.invoke(
        cli,
        [
            "claim",
            "declare",
            "--definition",
            str(definition),
            "--repository",
            "platform/core",
            "--agent-id",
            "agent-1",
            "--component",
            "web",
            "--json",
        ],
        obj={"config_path": None},
    )
    assert declared.exit_code == 0, declared.output
    payload = json.loads(declared.output)
    assert payload["component"] == "web"
    assert payload["patterns"] == ["apps/web/**"]

    missing = runner.invoke(
        cli,
        [
            "claim",
            "declare",
            "--definition",
            str(definition),
            "--repository",
            "platform/core",
            "--agent-id",
            "agent-2",
        ],
        obj={"config_path": None},
    )
    assert missing.exit_code != 0

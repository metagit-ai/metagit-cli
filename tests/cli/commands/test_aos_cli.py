#!/usr/bin/env python
"""CLI tests for aos/coord commands (RFC-0013)."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli

_WORKSPACE_YML = "\n".join(
    [
        "name: workspace",
        "kind: application",
        "workspace:",
        "  projects:",
        "    - name: alpha",
        "      repos: []",
    ]
)


def test_aos_and_coord_status_json(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
    runner = CliRunner()
    definition = str(tmp_path / ".metagit.yml")

    aos = runner.invoke(cli, ["aos", "status", "--definition", definition, "--json"])
    assert aos.exit_code == 0, aos.output
    payload = json.loads(aos.output)
    assert "subsystems" in payload
    assert "acl" in payload["subsystems"]
    assert "taskgraph" in payload["subsystems"]

    coord = runner.invoke(cli, ["coord", "status", "--definition", definition, "--json"])
    assert coord.exit_code == 0, coord.output
    assert "subsystems" in json.loads(coord.output)


def test_aos_doctor_fix_requires_yes(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["aos", "doctor", "--definition", str(tmp_path / ".metagit.yml"), "--fix"],
    )
    assert result.exit_code != 0


def test_aos_next_preview_json(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["aos", "next", "--definition", str(tmp_path / ".metagit.yml"), "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["committed"] is False

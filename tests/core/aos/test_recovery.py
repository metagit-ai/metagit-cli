#!/usr/bin/env python
"""Tests for AOS recovery recipes and recover/heartbeat (RFC-0019)."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli
from metagit.core.aos.models import AosFinding
from metagit.core.aos.recovery import build_recovery_recipes
from metagit.core.aos.service import AosService

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


def test_build_recovery_recipes_marks_unsafe_flags() -> None:
    findings = [
        AosFinding(severity="warning", code="orphan_claim", message="x", subsystem="acl"),
        AosFinding(severity="warning", code="stale_lease", message="y", subsystem="acl"),
    ]
    recipes = build_recovery_recipes(findings, agent_id="agent-1")
    actions = {item.action: item for item in recipes}
    assert actions["recover_agent"].safe_default is True
    assert actions["release_orphan_claims"].safe_default is False
    assert actions["release_orphan_claims"].requires_flag == "release_orphan_claims"


def test_aos_recover_requires_yes(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["aos", "recover", "--definition", str(tmp_path / ".metagit.yml"), "--agent-id", "a1"],
    )
    assert result.exit_code != 0


def test_aos_recover_and_doctor_recipes_json(tmp_path: Path) -> None:
    (tmp_path / ".metagit.yml").write_text(_WORKSPACE_YML + "\n", encoding="utf-8")
    runner = CliRunner()
    definition = str(tmp_path / ".metagit.yml")
    doctor = runner.invoke(cli, ["aos", "doctor", "--definition", definition, "--json"])
    assert doctor.exit_code == 0, doctor.output
    payload = json.loads(doctor.output)
    assert "recovery_recipes" in payload
    assert "findings" in payload

    recover = runner.invoke(
        cli,
        ["aos", "recover", "--definition", definition, "--agent-id", "agent-1", "--yes", "--json"],
    )
    assert recover.exit_code == 0, recover.output
    body = json.loads(recover.output)
    assert body["agent_id"] == "agent-1"
    assert "release_orphan_claims_requires_flag" in body["skipped"]

    heartbeat = runner.invoke(
        cli,
        ["aos", "heartbeat", "--definition", definition, "--agent-id", "agent-1", "--json"],
    )
    assert heartbeat.exit_code == 0, heartbeat.output
    hb = json.loads(heartbeat.output)
    assert hb["agent_id"] == "agent-1"
    assert hb["renewed"] == []


def test_recover_never_releases_claims_without_flag(tmp_path: Path) -> None:
    service = AosService(str(tmp_path))
    result = service.recover(agent_id="agent-1", confirm=True)
    assert not isinstance(result, Exception)
    assert "release_orphan_claims_requires_flag" in result.skipped

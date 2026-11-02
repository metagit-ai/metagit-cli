#!/usr/bin/env python
"""Local skill_sources resolve for validate and dispatch-plan."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from metagit import DEFAULT_CONFIG
from metagit.cli.main import cli

MANIFEST = """\
name: umbrella
kind: umbrella
workspace:
  agent_profile:
    skill_sources: [.agents/skills]
    skills: [my-skill]
    inherit: true
  projects:
    - name: billing
      repos:
        - name: api
          url: https://github.com/acme/api.git
"""


def _write(tmp_path: Path, *, sources: bool) -> Path:
    text = MANIFEST if sources else MANIFEST.replace("    skill_sources: [.agents/skills]\n", "")
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(text, encoding="utf-8")
    skill = tmp_path / ".agents" / "skills" / "my-skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# my skill\n", encoding="utf-8")
    return manifest


def test_local_skill_validates_and_dispatch_lists_path(tmp_path: Path) -> None:
    manifest = _write(tmp_path, sources=True)
    runner = CliRunner()
    validated = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "config", "-c", str(manifest), "validate"],
    )
    assert validated.exit_code == 0, validated.output
    planned = runner.invoke(
        cli,
        [
            "--config",
            DEFAULT_CONFIG,
            "agent",
            "dispatch-plan",
            "repo-implementer",
            "--root",
            str(tmp_path),
            "--project",
            "billing",
            "--repo",
            "api",
            "--json",
        ],
    )
    assert planned.exit_code == 0, planned.output
    payload = json.loads(planned.output)
    local = payload["local_skills"]
    assert local[0]["name"] == "my-skill"
    source = Path(local[0]["source_path"])
    assert source.parent.name == "my-skill"
    assert source.name == "SKILL.md"
    assert "my-skill" not in payload["required_profile_skills"]


def test_unknown_skill_lists_searched_directories(tmp_path: Path) -> None:
    manifest = _write(tmp_path, sources=False)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "config", "-c", str(manifest), "validate", "--json"],
    )
    assert result.exit_code != 0
    assert "unknown skill" in result.output
    assert "Searched:" in result.output


def test_profile_show_accepts_manifest_file_and_nested_cwd(tmp_path: Path) -> None:
    manifest = _write(tmp_path, sources=True)
    nested = tmp_path / "billing" / "api"
    nested.mkdir(parents=True)
    runner = CliRunner()
    shown = runner.invoke(
        cli,
        [
            "--config",
            DEFAULT_CONFIG,
            "agent",
            "profile",
            "show",
            "-p",
            "billing",
            "-n",
            "api",
            "--root",
            str(manifest),
            "--json",
        ],
    )
    assert shown.exit_code == 0, shown.output
    nested_show = runner.invoke(
        cli,
        [
            "--config",
            DEFAULT_CONFIG,
            "agent",
            "profile",
            "show",
            "-p",
            "billing",
            "-n",
            "api",
            "--root",
            str(nested),
            "--json",
        ],
    )
    assert nested_show.exit_code == 0, nested_show.output
    assert "my-skill" in nested_show.output

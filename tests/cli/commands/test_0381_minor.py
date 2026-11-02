#!/usr/bin/env python
"""Minor 0.38.1 CLI fixes: project -c, help, dispatch skills, duplicate warnings."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from metagit import DEFAULT_CONFIG
from metagit.cli.main import cli

MANIFEST = """\
name: demo
kind: umbrella
workspace:
  agent_profile:
    skill_sources:
      - .agents/skills
    skills:
      - my-skill
    inherit: true
  projects:
    - name: billing
      repos:
        - name: api
          url: https://github.com/acme/api.git
    - name: platform
      repos:
        - name: worker
          url: https://github.com/acme/api.git
"""


def _text(result: object) -> str:
    output = getattr(result, "output", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    return f"{output}\n{stderr}"


def _invoke(args: list[str], *, cwd: Path | None = None) -> object:
    runner = CliRunner()
    if cwd is None:
        return runner.invoke(cli, args)
    with runner.isolated_filesystem(temp_dir=cwd):
        return runner.invoke(cli, args)


def test_project_list_accepts_config_after_subcommand(tmp_path: Path) -> None:
    manifest = tmp_path / "workspace" / ".metagit.yml"
    manifest.parent.mkdir()
    manifest.write_text(MANIFEST, encoding="utf-8")
    result = _invoke(
        ["--config", DEFAULT_CONFIG, "project", "list", "-c", str(manifest), "--json"],
        cwd=tmp_path,
    )
    assert result.exit_code == 0, _text(result)
    assert "billing" in _text(result)


def test_project_list_help_without_manifest(tmp_path: Path) -> None:
    result = _invoke(
        ["--config", DEFAULT_CONFIG, "project", "list", "--help"],
        cwd=tmp_path,
    )
    assert result.exit_code == 0, _text(result)
    assert "Configuration file not found" not in _text(result)
    workspace = _invoke(
        ["--config", DEFAULT_CONFIG, "workspace", "list", "--help"],
        cwd=tmp_path,
    )
    assert workspace.exit_code == 0, _text(workspace)
    assert "Configuration file not found" not in _text(workspace)


def test_dispatch_plan_project_scope_fills_local_skills(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(MANIFEST, encoding="utf-8")
    skill = tmp_path / ".agents" / "skills" / "my-skill" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: my-skill\ndescription: synthetic\n---\n", encoding="utf-8")
    result = _invoke(
        [
            "--config",
            DEFAULT_CONFIG,
            "agent",
            "dispatch-plan",
            "catalog-bootstrapper",
            "-c",
            str(manifest),
            "--root",
            str(tmp_path),
            "-p",
            "billing",
            "--json",
        ],
        cwd=tmp_path,
    )
    assert result.exit_code == 0, _text(result)
    payload = json.loads(result.output)
    assert payload["local_skills"][0]["name"] == "my-skill"


def test_duplicate_repo_warning_prints_manifest_path(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(
        """\
name: demo
kind: umbrella
workspace:
  projects:
    - name: billing
      repos:
        - name: api
          url: https://github.com/acme/api.git
    - name: platform
      repos:
        - name: worker
          url: https://github.com/acme/api.git
""",
        encoding="utf-8",
    )
    result = _invoke(
        ["--config", DEFAULT_CONFIG, "config", "validate", "-c", str(manifest)],
        cwd=tmp_path,
    )
    rendered = _text(result)
    assert result.exit_code == 0, rendered
    assert "None:" not in rendered
    assert str(manifest) in rendered

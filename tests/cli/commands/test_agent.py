#!/usr/bin/env python
"""CLI tests for metagit agent command."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from metagit.cli.main import cli


def test_agent_list() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["agent", "list"])
    assert result.exit_code == 0, result.output
    assert "orchestration-overseer" in result.output


def test_agent_list_json() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["agent", "list", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema_version"] == "1.0"
    ids = [item["id"] for item in payload["templates"]]
    assert "orchestration-overseer" in ids
    assert len(ids) >= 10


def test_agent_validate() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["agent", "validate"])
    assert result.exit_code == 0, result.output
    assert "validated" in result.output.lower()


def test_agent_schema_writes_file() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            ["agent", "schema", "--output-path", "agent.schema.json"],
        )
        assert result.exit_code == 0, result.output
        schema = json.loads(Path("agent.schema.json").read_text(encoding="utf-8"))
        assert "AgentTemplateManifest" in schema.get("title", "")


def test_agent_preview_json() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "agent",
            "preview",
            "repo-implementer",
            "--vendor",
            "claude_code",
            "--no-prompt",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["template_id"] == "repo-implementer"
    assert "Repo implementer" in payload["content"]


def test_agent_export_no_prompt() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "agent",
                "export",
                "orchestration-overseer",
                "--no-prompt",
                "-o",
                "out",
            ],
        )
        assert result.exit_code == 0, result.output
        agent_path = Path("out/orchestration-overseer.md")
        assert agent_path.is_file()
        assert "orchestration-overseer" in agent_path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "vendor,path_suffix",
    [
        ("cursor", ".cursor/agents/orchestration-overseer.md"),
        ("opencode", ".opencode/agents/orchestration-overseer.md"),
        ("hermes", ".hermes/skills/orchestration-overseer/SKILL.md"),
        ("github_copilot", ".github/agents/orchestration-overseer.agent.md"),
        ("windsurf", ".windsurf/skills/orchestration-overseer/SKILL.md"),
        ("codex", ".agents/skills/orchestration-overseer/SKILL.md"),
    ],
)
def test_agent_create_vendor_dry_run(vendor: str, path_suffix: str) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "agent",
                "create",
                "orchestration-overseer",
                "--vendor",
                vendor,
                "--no-prompt",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Would write agent" in result.output
        assert Path(path_suffix).name in result.output


def test_agent_create_claude_code_dry_run() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "agent",
                "create",
                "orchestration-overseer",
                "--vendor",
                "claude_code",
                "--no-prompt",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Would write agent" in result.output
        assert "orchestration-overseer.md" in result.output

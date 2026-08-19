#!/usr/bin/env python
"""CLI tests for capability command surface."""

from __future__ import annotations

import json
import os
from pathlib import Path

from click.testing import CliRunner

from metagit.cli.main import cli


def _env(root: Path) -> dict[str, str]:
    return {**os.environ, "METAGIT_WORKSPACE_PATH": str(root.resolve())}


def _write_fixture(root: Path) -> None:
    (root / ".metagit.yml").write_text(
        "\n".join(
            [
                "name: workspace",
                "kind: application",
                "routing:",
                "  catalog: knowledge/requests/entries",
                "  runs: knowledge/requests/runs",
                "workspace:",
                "  projects:",
                "    - name: infra",
                "      tags:",
                "        project_type: iac",
                "      repos:",
                "        - name: terraform-vpc",
                "          path: repos/terraform-vpc",
                "          language: hcl",
                "          tags:",
                "            iac: terraform",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    repo = root / "repos" / "terraform-vpc"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "main.tf").write_text("resource \"null_resource\" \"demo\" {}\n", encoding="utf-8")
    entries = root / "knowledge" / "requests" / "entries"
    entries.mkdir(parents=True, exist_ok=True)
    (entries / "REQ-TF.yml").write_text(
        "\n".join(
            [
                "id: REQ-TF",
                "title: Terraform module change",
                "triggers: [terraform module change]",
                "capability:",
                "  selector:",
                "    project_types: [iac]",
                "  workflow:",
                "    - {name: inspect}",
                "  expected_output: report",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_capability_resolve_json_success() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp:
        root = Path(tmp)
        _write_fixture(root)
        result = runner.invoke(
            cli,
            ["capability", "resolve", "terraform module change", "--project", "infra", "--json"],
            env=_env(root),
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["ok"] is True
        assert payload["matches"][0]["capability_id"] == "REQ-TF"


def test_capability_compile_json_success() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem() as tmp:
        root = Path(tmp)
        _write_fixture(root)
        result = runner.invoke(
            cli,
            [
                "capability",
                "compile",
                "--id",
                "REQ-TF",
                "--project",
                "infra",
                "--repo",
                "terraform-vpc",
                "--no-context",
                "--json",
            ],
            env=_env(root),
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["capability_id"] == "REQ-TF"
        assert payload["repository"]["repo"] == "terraform-vpc"


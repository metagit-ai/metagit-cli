#!/usr/bin/env python
"""Duplicate repository declarations are warnings, and errors with --strict."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from metagit import DEFAULT_CONFIG
from metagit.cli.main import cli

ROOT = """\
name: umbrella
kind: umbrella
includes:
  - .metagit.d/projects/billing.yml
  - .metagit.d/projects/other.yml
  - .metagit.d/graph/nodes.yml
  - .metagit.d/graph/relationships.yml
"""

BILLING = """\
workspace:
  projects:
    - name: billing
      repos:
        - name: api
          url: https://github.com/Acme/API.git
"""

OTHER = """\
workspace:
  projects:
    - name: other
      repos:
        - name: clone
          url: git@github.com:acme/api.git
"""

NODES = """\
graph:
  nodes:
    - identity: github://acme/api
      name: api
"""

RELATIONSHIPS = """\
graph:
  relationships:
    - id: edge
      from:
        identity: github://acme/api
      to:
        project: billing
        repo: api
      type: depends_on
"""


def _write(tmp_path: Path) -> Path:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(ROOT, encoding="utf-8")
    projects = tmp_path / ".metagit.d" / "projects"
    graph = tmp_path / ".metagit.d" / "graph"
    projects.mkdir(parents=True)
    graph.mkdir()
    (projects / "billing.yml").write_text(BILLING, encoding="utf-8")
    (projects / "other.yml").write_text(OTHER, encoding="utf-8")
    (graph / "nodes.yml").write_text(NODES, encoding="utf-8")
    (graph / "relationships.yml").write_text(RELATIONSHIPS, encoding="utf-8")
    return manifest


def test_duplicate_repo_warns_and_strict_fails(tmp_path: Path) -> None:
    manifest = _write(tmp_path)
    runner = CliRunner()
    warned = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "config", "-c", str(manifest), "validate"],
    )
    assert warned.exit_code == 0, warned.output
    text = warned.output + (getattr(warned, "stderr", None) or "")
    assert "billing.yml" in text
    assert "other.yml" in text
    assert "warning:" in text

    strict = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "config", "-c", str(manifest), "validate", "--strict"],
    )
    assert strict.exit_code != 0
    strict_text = strict.output + (getattr(strict, "stderr", None) or "")
    assert "Traceback" not in strict_text
    assert "billing.yml" in strict_text
    assert "other.yml" in strict_text

    reported = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "config", "-c", str(manifest), "validate", "--json"],
    )
    assert reported.exit_code == 0, reported.output
    payload = json.loads(reported.output)
    assert payload["ok"] is True
    codes = {item["code"] for item in payload["warnings"]}
    assert codes == {
        "duplicate_repo_url",
        "graph_node_duplicates_project_repo",
        "relationship_identity_for_project_repo",
    }
    duplicate = next(item for item in payload["warnings"] if item["code"] == "duplicate_repo_url")
    files = {Path(str(item["file"])).name for item in duplicate["locations"]}
    assert files == {"billing.yml", "other.yml"}
    assert any("repos[name=api]" in item["path"] for item in duplicate["locations"])
    assert any("repos[name=clone]" in item["path"] for item in duplicate["locations"])

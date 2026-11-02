#!/usr/bin/env python
"""Composed repo and graph listings match for split and single-file manifests."""

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
  projects:
    - name: billing
      repos:
        - name: api
          url: https://github.com/acme/api.git
          tags:
            kind: service
graph:
  nodes:
    - identity: github://acme/api
      name: api
  relationships:
    - id: edge
      from_endpoint:
        project: billing
        repo: api
      to:
        project: billing
        repo: api
      type: depends_on
"""


def _without_source(payload: list[dict]) -> list[dict]:
    return [{key: value for key, value in item.items() if key != "source"} for item in payload]


def test_split_and_single_file_listings_match(tmp_path: Path) -> None:
    single = tmp_path / "single"
    split = tmp_path / "split"
    single.mkdir()
    split.mkdir()
    (single / ".metagit.yml").write_text(MANIFEST, encoding="utf-8")
    manifest = split / ".metagit.yml"
    manifest.write_text(MANIFEST, encoding="utf-8")
    runner = CliRunner()
    divided = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "config", "-c", str(manifest), "split", "--by", "all"],
    )
    assert divided.exit_code == 0, divided.output

    def invoke(root: Path, *args: str) -> list[dict]:
        result = runner.invoke(
            cli,
            ["--config", DEFAULT_CONFIG, *args, "-c", str(root / ".metagit.yml"), "--json"],
        )
        assert result.exit_code == 0, result.output
        return json.loads(result.output)

    single_repos = invoke(single, "repo", "list", "--all")
    split_repos = invoke(split, "repo", "list", "--all")
    assert _without_source(single_repos) == _without_source(split_repos)
    assert single_repos[0]["kind"] == "service"
    assert single_repos[0]["url"] == "https://github.com/acme/api.git"
    assert single_repos[0]["source"] == ".metagit.yml"
    assert split_repos[0]["source"].endswith("billing.yml")

    assert _without_source(invoke(single, "graph", "nodes")) == _without_source(invoke(split, "graph", "nodes"))
    single_edges = invoke(single, "graph", "relationships")
    split_edges = invoke(split, "graph", "relationships")
    assert _without_source(single_edges) == _without_source(split_edges)
    assert single_edges[0]["from_endpoint"]["repo"] == "api"
    assert split_edges[0]["source"].endswith("relationships.yml")

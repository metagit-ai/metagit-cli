#!/usr/bin/env python
"""Split keeps long scalars intact and fmt --check stays clean."""

from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from metagit import DEFAULT_CONFIG
from metagit.cli.main import cli
from metagit.core.config.manifest_diff import diff_manifests, diff_values

PLAIN = (
    "alpha — a real modelled endpoint using `checkout` code, ratio:3, and hash#token "
    "before the writer width would fold a plain scalar into a block " + ("word " * 16)
).strip()
QUOTED = (
    'she said \\"hello\\" about a real modelled endpoint with `ticks`, ratio:3, and hash#token ' + ("word " * 16)
).strip()
assert 150 <= len(PLAIN) <= 400
assert 150 <= len(QUOTED) <= 400

LONG_SCALARS = f"""\
name: umbrella
kind: umbrella
description: >-
  folded workspace text stays one paragraph
  even when the next line is long enough to pass the writer width marker
workspace:
  projects:
    - name: billing
      description: {PLAIN}
      repos:
        - name: api
          description: "{QUOTED}"
          url: https://github.com/acme/api.git
        - name: worker
          description: |
            literal line one
            literal line two
          url: https://github.com/acme/worker.git
    - name: identity
      description: |-
        strip line one
        strip line two
      repos:
        - name: login
          url: https://github.com/acme/login.git
graph:
  nodes:
    - identity: github://acme/api
      name: api
      metadata:
        summary: {PLAIN}
  relationships:
    - id: edge-1
      description: "{QUOTED}"
      from_endpoint:
        project: billing
        repo: api
      to:
        project: identity
        repo: login
      type: depends_on
"""


def test_inner_newline_is_a_value_difference() -> None:
    kinds = {
        item.path: item.kind
        for item in diff_values(
            {"description": "alpha beta", "title": "alpha"},
            {"description": "alpha\nbeta", "title": "alpha\n"},
        )
    }
    assert kinds["description"] == "value"
    assert kinds["title"] == "whitespace-only"


def test_split_preserves_long_scalars_and_passes_fmt_check(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(LONG_SCALARS, encoding="utf-8")
    original = tmp_path / "original.yml"
    original.write_text(LONG_SCALARS, encoding="utf-8")
    before = yaml.safe_load(LONG_SCALARS)
    runner = CliRunner()
    split = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "config", "-c", str(manifest), "split", "--by", "all"],
    )
    assert split.exit_code == 0, split.output
    diffs = diff_manifests(str(original), str(manifest), mode="raw", cwd=tmp_path)
    assert diffs == [], [(item.path, item.kind) for item in diffs]
    check = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "fmt", "-t", "metagit", "--metagit-path", str(manifest), "--check"],
    )
    assert check.exit_code == 0, check.output
    composed = yaml.safe_load((tmp_path / ".metagit.d" / "projects" / "billing.yml").read_text(encoding="utf-8"))
    billing = composed["workspace"]["projects"][0]
    assert billing["description"] == before["workspace"]["projects"][0]["description"]
    assert "\n" not in billing["description"]
    assert "\n" not in billing["repos"][0]["description"]


def test_split_glob_preserves_long_scalars(tmp_path: Path) -> None:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(LONG_SCALARS, encoding="utf-8")
    original = tmp_path / "original.yml"
    original.write_text(LONG_SCALARS, encoding="utf-8")
    runner = CliRunner()
    split = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "config", "-c", str(manifest), "split", "--by", "all", "--glob"],
    )
    assert split.exit_code == 0, split.output
    diffs = diff_manifests(str(original), str(manifest), mode="raw", cwd=tmp_path)
    assert diffs == [], [(item.path, item.kind) for item in diffs]
    check = runner.invoke(
        cli,
        ["--config", DEFAULT_CONFIG, "fmt", "-t", "metagit", "--metagit-path", str(manifest), "--check"],
    )
    assert check.exit_code == 0, check.output

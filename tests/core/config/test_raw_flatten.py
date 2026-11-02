#!/usr/bin/env python
"""Lossless flatten: split then flatten keeps the parsed manifest."""

from __future__ import annotations

from pathlib import Path

from metagit.core.config.include_writer import flatten_manifest, split_manifest
from metagit.core.config.raw_compose import parsed_without_includes
from metagit.manifest import load_composed

FIDELITY = """\
name: umbrella
kind: umbrella
description: |
  line one
  line two
workspace:
  description: shared
  agent_profile:
    inherit: true
  projects:
    # billing stays first
    - name: billing  # primary
      description: >-
        folded
        text
      tags:
        team: pay
      repos:
        - name: api
          description: "quoted\\nmulti"
          url: https://github.com/acme/api.git
    - name: identity
      description: plain
      repos: []
documentation:
  - kind: markdown
    path: docs/guide.md
    title: guide
    tags:
      topic: onboarding
graph:
  nodes:
    - identity: github://acme/api
      name: api
  relationships:
    - id: edge-1
      from_endpoint:
        project: billing
        repo: api
      to:
        project: identity
      type: depends_on
"""


def _write(tmp_path: Path) -> Path:
    manifest = tmp_path / ".metagit.yml"
    manifest.write_text(FIDELITY, encoding="utf-8")
    return manifest


def test_split_then_flatten_matches_parsed_source(tmp_path: Path) -> None:
    manifest = _write(tmp_path)
    original = parsed_without_includes(manifest.read_text(encoding="utf-8"))
    planned = split_manifest(manifest, by="all", directory=Path(".metagit.d"), dry_run=False)
    assert not isinstance(planned, Exception)
    flattened = flatten_manifest(manifest)
    assert isinstance(flattened, str)
    assert parsed_without_includes(flattened) == original
    assert "from_endpoint:" in flattened
    assert "type: depends_on" in flattened
    assert "topic:" in flattened


def test_flatten_in_place_round_trips(tmp_path: Path) -> None:
    manifest = _write(tmp_path)
    original = parsed_without_includes(manifest.read_text(encoding="utf-8"))
    assert not isinstance(split_manifest(manifest, by="all", directory=Path(".metagit.d"), dry_run=False), Exception)
    rendered = flatten_manifest(manifest, in_place=True)
    assert isinstance(rendered, str)
    assert "includes:" not in manifest.read_text(encoding="utf-8")
    assert parsed_without_includes(manifest.read_text(encoding="utf-8")) == original


def test_load_composed_matches_for_split_and_single_file(tmp_path: Path) -> None:
    single_dir = tmp_path / "single"
    split_dir = tmp_path / "split"
    single_dir.mkdir()
    split_dir.mkdir()
    single = single_dir / ".metagit.yml"
    split_root = split_dir / ".metagit.yml"
    single.write_text(FIDELITY, encoding="utf-8")
    split_root.write_text(FIDELITY, encoding="utf-8")
    assert not isinstance(split_manifest(split_root, by="all", directory=Path(".metagit.d"), dry_run=False), Exception)
    assert load_composed(split_root) == load_composed(single)


def test_normalized_flatten_still_uses_the_model(tmp_path: Path) -> None:
    manifest = _write(tmp_path)
    assert not isinstance(split_manifest(manifest, by="all", directory=Path(".metagit.d"), dry_run=False), Exception)
    rendered = flatten_manifest(manifest, normalized=True)
    assert isinstance(rendered, str)
    assert "from_endpoint:" not in rendered
    assert "from:" in rendered

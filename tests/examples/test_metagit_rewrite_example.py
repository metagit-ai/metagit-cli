#!/usr/bin/env python
"""Tests for the metagit-rewrite workspace example."""

from pathlib import Path

import yaml

from metagit.core.config.manager import MetagitConfigManager


def test_rewrite_example_manifest_validates() -> None:
  manifest = Path("examples/metagit-rewrite/.metagit.yml")
  manager = MetagitConfigManager(str(manifest))
  loaded = manager.load_config()
  assert not isinstance(loaded, Exception)
  assert loaded.kind == "umbrella"
  rewrite = next(p for p in loaded.workspace.projects if p.name == "rewrite")
  repo_names = {repo.name for repo in rewrite.repos}
  assert repo_names == {"source", "target"}


def test_rewrite_example_campaign_fixture_shape() -> None:
  campaign = yaml.safe_load(
    Path("examples/metagit-rewrite/_campaigns/language-rewrite.example.yml").read_text(
      encoding="utf-8",
    )
  )
  assert campaign["slug"] == "language-rewrite"
  assert campaign["reference_impl"] == "rewrite/source"
  assert len(campaign["repos"]) == 2

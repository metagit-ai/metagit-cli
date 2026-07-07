#!/usr/bin/env python
"""Tests for metagit init template service."""

from pathlib import Path

import yaml

from metagit.core.init.service import InitService


def test_list_templates_includes_hermes() -> None:
  service = InitService()
  ids = {item.id for item in service.list_templates()}
  assert "application" in ids
  assert "umbrella" in ids
  assert "hermes-orchestrator" in ids
  assert "metagit-rewrite" in ids


def test_init_rewrite_with_answers_file(tmp_path: Path) -> None:
  service = InitService()
  answers = tmp_path / "answers.yml"
  answers.write_text(
    yaml.safe_dump(
      {
        "name": "rewrite-control",
        "description": "Test rewrite workspace",
        "url": "",
        "source_repo_name": "source",
        "source_repo_url": "https://github.com/example/source.git",
        "target_repo_name": "target",
        "target_repo_url": "https://github.com/example/target.git",
        "campaign_slug": "language-rewrite",
      }
    ),
    encoding="utf-8",
  )
  target = tmp_path / "coordinator"
  target.mkdir()
  result = service.initialize(
    target,
    template_id="metagit-rewrite",
    directory_name="coordinator",
    git_remote_url=None,
    answers_file=answers,
    no_prompt=True,
    force=True,
  )
  manifest = yaml.safe_load((target / ".metagit.yml").read_text(encoding="utf-8"))
  assert manifest["name"] == "rewrite-control"
  rewrite = next(p for p in manifest["workspace"]["projects"] if p["name"] == "rewrite")
  assert rewrite["repos"][0]["url"] == "https://github.com/example/source.git"
  assert (target / "_campaigns" / "language-rewrite.yml").is_file()
  assert (target / "_rewrite" / "parity-registry.yml").is_file()
  assert result.metagit_yml.is_file()


def test_init_hermes_with_answers_file(tmp_path: Path) -> None:
  service = InitService()
  answers = tmp_path / "answers.yml"
  answers.write_text(
    yaml.safe_dump(
      {
        "name": "test-control",
        "description": "Test Hermes workspace",
        "url": "",
        "portfolio_repo_name": "api",
        "portfolio_repo_url": "https://github.com/example/api.git",
        "local_site_name": "site",
        "local_site_path": "/tmp/site",
      }
    ),
    encoding="utf-8",
  )
  target = tmp_path / "coordinator"
  target.mkdir()
  result = service.initialize(
    target,
    template_id="hermes-orchestrator",
    directory_name="coordinator",
    git_remote_url=None,
    answers_file=answers,
    no_prompt=True,
    force=True,
  )
  manifest = yaml.safe_load((target / ".metagit.yml").read_text(encoding="utf-8"))
  assert manifest["name"] == "test-control"
  assert manifest["kind"] == "umbrella"
  assert (target / "AGENTS.md").is_file()
  local = next(p for p in manifest["workspace"]["projects"] if p["name"] == "local")
  assert local["repos"][0]["path"] == "/tmp/site"
  assert result.metagit_yml.is_file()


def test_init_minimal_library_kind(tmp_path: Path) -> None:
  service = InitService()
  target = tmp_path / "lib"
  target.mkdir()
  service.initialize_minimal(
    target,
    kind="library",
    name="my-lib",
    description="A library.",
    url=None,
    force=True,
  )
  manifest = yaml.safe_load((target / ".metagit.yml").read_text(encoding="utf-8"))
  assert manifest["kind"] == "library"
  assert manifest["name"] == "my-lib"


def test_init_minimal_idempotent_when_manifest_valid(tmp_path: Path) -> None:
  service = InitService()
  target = tmp_path / "lib"
  target.mkdir()
  service.initialize_minimal(
    target,
    kind="library",
    name="my-lib",
    description="A library.",
    url=None,
  )
  result = service.initialize_minimal(
    target,
    kind="library",
    name="other-name",
    description="Would overwrite.",
    url=None,
  )
  assert result.already_exists is True
  manifest = yaml.safe_load((target / ".metagit.yml").read_text(encoding="utf-8"))
  assert manifest["name"] == "my-lib"


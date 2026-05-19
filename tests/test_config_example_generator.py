#!/usr/bin/env python
"""Tests for MetagitConfig exemplar generation."""

from metagit.core.config.example_generator import (
  ConfigExampleGenerator,
  load_example_overrides,
)
from metagit.core.config.models import MetagitConfig


def test_render_yaml_includes_header_and_workspace() -> None:
  generator = ConfigExampleGenerator(overrides=load_example_overrides())
  rendered = generator.render_yaml(include_workspace=True, comment_style="line")
  assert "NON-PRODUCTION EXEMPLAR" in rendered
  assert "workspace:" in rendered
  assert "hermes-control-plane" in rendered or "example-umbrella" in rendered


def test_build_merges_overrides() -> None:
  generator = ConfigExampleGenerator(overrides={"name": "override-name"})
  payload = generator.build(include_workspace=False)
  assert payload["name"] == "override-name"
  assert "workspace" not in payload


def test_generated_payload_validates_when_overrides_used() -> None:
  generator = ConfigExampleGenerator(overrides=load_example_overrides())
  payload = generator.build(include_workspace=True)
  config = MetagitConfig.model_validate(payload)
  assert config.name == payload["name"]
  assert config.workspace is not None
  assert any(project.name == "local" for project in config.workspace.projects)

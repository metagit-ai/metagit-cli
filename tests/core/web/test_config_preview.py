#!/usr/bin/env python
"""Tests for config YAML preview rendering."""

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.web.config_preview import (
  redact_secrets,
  render_appconfig_yaml,
  render_metagit_yaml,
)


def test_render_metagit_yaml_normalized() -> None:
  config = MetagitConfig.model_validate({"name": "demo", "kind": "application"})
  rendered = render_metagit_yaml(config, style="normalized")
  assert "name: demo" in rendered
  assert "kind: application" in rendered


def test_render_appconfig_yaml_masks_secrets() -> None:
  config = AppConfig.model_validate(
    {
      "workspace": {"path": "./sync"},
      "providers": {
        "github": {"enabled": True, "api_token": "ghp_abcdefghijklmnop"},
      },
    }
  )
  rendered = render_appconfig_yaml(
    config,
    config_path="/tmp/metagit.config.yaml",
    style="normalized",
    mask_secrets=True,
  )
  assert "ghp_abcdefghijklmnop" not in rendered
  assert "***mnop" in rendered


def test_redact_secrets_nested() -> None:
  payload = {"providers": {"gitlab": {"api_token": "glpat-secret"}}}
  redacted = redact_secrets(payload)
  assert redacted["providers"]["gitlab"]["api_token"] == "***cret"

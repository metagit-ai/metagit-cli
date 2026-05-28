#!/usr/bin/env python
"""Tests for round-trip YAML formatting."""

from __future__ import annotations

from metagit.core.appconfig.models import AppConfig
from metagit.core.config.models import MetagitConfig
from metagit.core.config.schema_urls import (
    METAGIT_APPCONFIG_SCHEMA_URL,
    METAGIT_CONFIG_SCHEMA_URL,
    schema_language_server_comment,
)
from metagit.core.config.yaml_roundtrip import format_yaml_document


def test_format_yaml_document_preserves_inline_comments() -> None:
    original = """\
# yaml-language-server: $schema=https://example.com/old.schema.json
documentation:
  # keep this note
  - README.md
name: demo
"""
    ordered = {"name": "demo", "documentation": ["README.md"]}
    rendered = format_yaml_document(
        original,
        ordered,
        MetagitConfig,
        schema_url=METAGIT_CONFIG_SCHEMA_URL,
    )
    assert schema_language_server_comment(METAGIT_CONFIG_SCHEMA_URL) in rendered
    assert "# keep this note" in rendered
    assert rendered.index("name: demo") < rendered.index("documentation:")


def test_format_yaml_document_uses_two_space_indentation() -> None:
    original = "name: demo\n"
    ordered = {
        "name": "demo",
        "workspace": {"projects": [{"name": "default", "repos": []}]},
    }
    rendered = format_yaml_document(
        original,
        ordered,
        MetagitConfig,
        schema_url=METAGIT_CONFIG_SCHEMA_URL,
    )
    assert "\n  projects:\n    - name: default" in rendered
    assert "\n      repos:" in rendered


def test_format_yaml_document_indents_top_level_list_items() -> None:
    original = """\
name: demo
documentation:
- kind: markdown
  path: README.md
"""
    ordered = {
        "name": "demo",
        "documentation": [{"kind": "markdown", "path": "README.md"}],
    }
    rendered = format_yaml_document(
        original,
        ordered,
        MetagitConfig,
        schema_url=METAGIT_CONFIG_SCHEMA_URL,
    )
    assert "\ndocumentation:\n  - kind: markdown" in rendered
    assert "\n    path: README.md" in rendered


def test_format_yaml_document_preserves_repo_list_comments() -> None:
    original = """\
# yaml-language-server: $schema=https://example.com/old.schema.json
workspace:
  projects:
  - name: default
    repos:
    # billing service
    - name: billing
      url: https://github.com/example/billing.git
"""
    ordered = {
        "name": "demo",
        "workspace": {
            "projects": [
                {
                    "name": "default",
                    "repos": [
                        {
                            "name": "billing",
                            "url": "https://github.com/example/billing.git",
                        }
                    ],
                }
            ]
        },
    }
    rendered = format_yaml_document(
        original,
        ordered,
        MetagitConfig,
        schema_url=METAGIT_CONFIG_SCHEMA_URL,
    )
    assert "# billing service" in rendered
    assert "name: billing" in rendered


def test_format_yaml_document_preserves_multiline_description() -> None:
    original = """\
name: demo
description: |
  Line one of the description.
  Line two of the description.
"""
    ordered = {
        "name": "demo",
        "description": (
            "Line one of the description.\nLine two of the description."
        ),
    }
    rendered = format_yaml_document(
        original,
        ordered,
        MetagitConfig,
        schema_url=METAGIT_CONFIG_SCHEMA_URL,
    )
    assert "description: |" in rendered
    assert "  Line one of the description." in rendered
    assert "  Line two of the description." in rendered


def test_format_yaml_document_uses_literal_block_for_long_description() -> None:
    long_text = "A" * 105
    original = f"name: demo\ndescription: {long_text}\n"
    ordered = {"name": "demo", "description": long_text}
    rendered = format_yaml_document(
        original,
        ordered,
        MetagitConfig,
        schema_url=METAGIT_CONFIG_SCHEMA_URL,
    )
    assert "description: |" in rendered
    assert long_text in rendered


def test_format_appconfig_wraps_config_and_adds_schema_comment() -> None:
    original = """\
config:
  description: app settings
  agent_mode: false
"""
    ordered = {"description": "app settings", "agent_mode": False}
    rendered = format_yaml_document(
        original,
        ordered,
        AppConfig,
        schema_url=METAGIT_APPCONFIG_SCHEMA_URL,
        wrapper_key="config",
    )
    assert schema_language_server_comment(METAGIT_APPCONFIG_SCHEMA_URL) in rendered
    assert "config:\n  agent_mode:" in rendered
    assert "  description: app settings" in rendered

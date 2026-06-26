#!/usr/bin/env python
"""Published JSON Schema URLs for Metagit YAML files."""

from __future__ import annotations

GITHUB_SCHEMA_BASE = "https://raw.githubusercontent.com/metagit-ai/metagit-cli/refs/heads/main/schemas"
METAGIT_CONFIG_SCHEMA_URL = f"{GITHUB_SCHEMA_BASE}/metagit_config.schema.json"
METAGIT_APPCONFIG_SCHEMA_URL = f"{GITHUB_SCHEMA_BASE}/metagit_appconfig.schema.json"
SCHEMA_COMMENT_PREFIX = "# yaml-language-server: $schema="


def schema_language_server_directive(schema_url: str) -> str:
    """Return the yaml-language-server schema directive without a leading ``#``."""
    return f"yaml-language-server: $schema={schema_url}"


def schema_language_server_comment(schema_url: str) -> str:
    """Return the yaml-language-server schema directive line."""
    return f"{SCHEMA_COMMENT_PREFIX}{schema_url}"

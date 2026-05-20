#!/usr/bin/env python
"""
Render full application configuration for CLI display.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from metagit.core.appconfig.agent_mode import resolve_agent_mode
from metagit.core.appconfig.models import AppConfig
from metagit.core.config.yaml_display import dump_config_dict

OutputFormat = Literal["yaml", "json", "minimal-yaml"]


def build_appconfig_payload(
    config: AppConfig,
    *,
    config_path: str,
    minimal: bool = False,
) -> dict[str, Any]:
    """Build the document shown by `metagit appconfig show`."""
    if minimal:
        config_body = config.model_dump(
            exclude_none=True,
            exclude_defaults=True,
            mode="json",
        )
    else:
        config_body = config.model_dump(mode="json")
    return {
        "config_path": config_path,
        "agent_mode": resolve_agent_mode(config),
        "config": config_body,
    }


def render_appconfig_show(
    config: AppConfig,
    *,
    config_path: str,
    output_format: OutputFormat = "yaml",
    minimal: bool = False,
) -> str:
    """Serialize appconfig show output for the requested format."""
    payload = build_appconfig_payload(
        config,
        config_path=config_path,
        minimal=minimal,
    )
    if output_format == "json":
        return json.dumps(payload, indent=2, default=str) + "\n"
    if output_format == "minimal-yaml":
        return dump_config_dict({"config": payload["config"]})
    return dump_config_dict(payload)
